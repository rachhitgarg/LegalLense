import { useState, useEffect, useRef } from 'react'
import './ChatInterface.css'

const API_URL = import.meta.env.DEV ? 'http://localhost:8888/api' : '/api'

// Generate session ID once
const getSessionId = () => {
    let sessionId = localStorage.getItem('legal_lens_session')
    if (!sessionId) {
        sessionId = 'session_' + Math.random().toString(36).substring(2, 15)
        localStorage.setItem('legal_lens_session', sessionId)
    }
    return sessionId
}

interface Message {
    role: 'user' | 'assistant'
    content: string
    timestamp: number
    citations?: { title: string; docId: string }[]
    sources?: { docId: string; title: string; score: number }[]
}

interface ChatInterfaceProps {
    onViewDocument?: (docId: string, highlight?: string) => void
}

export default function ChatInterface({ onViewDocument }: ChatInterfaceProps) {
    const [messages, setMessages] = useState<Message[]>([])
    const [input, setInput] = useState('')
    const [isStreaming, setIsStreaming] = useState(false)
    const [streamingText, setStreamingText] = useState('')
    const [error, setError] = useState<string | null>(null)
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const sessionId = useRef(getSessionId())

    // Load message history from localStorage on mount
    useEffect(() => {
        const saved = localStorage.getItem(`chat_history_${sessionId.current}`)
        if (saved) {
            try {
                setMessages(JSON.parse(saved))
            } catch (e) {
                console.error('Failed to load chat history:', e)
            }
        }
    }, [])

    // Save messages to localStorage when they change
    useEffect(() => {
        if (messages.length > 0) {
            localStorage.setItem(`chat_history_${sessionId.current}`, JSON.stringify(messages))
        }
    }, [messages])

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages, streamingText])

    const sendMessage = async () => {
        if (!input.trim() || isStreaming) return

        const userMessage: Message = {
            role: 'user',
            content: input.trim(),
            timestamp: Date.now()
        }

        setMessages(prev => [...prev, userMessage])
        setInput('')
        setIsStreaming(true)
        setStreamingText('')
        setError(null)

        try {
            // Prepare history for API (last 10 messages)
            const history = messages.slice(-10).map(m => ({
                role: m.role,
                content: m.content
            }))

            const response = await fetch(`${API_URL}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: userMessage.content,
                    sessionId: sessionId.current,
                    history
                })
            })

            if (!response.ok) {
                throw new Error(`API error: ${response.status}`)
            }

            const text = await response.text()
            const lines = text.split('\n')

            let fullText = ''
            let finalMetadata: { citations?: any[]; sources?: any[] } = {}

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6)
                    try {
                        const parsed = JSON.parse(data)
                        console.log('SSE parsed:', parsed) // Debug log
                        if (parsed.text) {
                            fullText += parsed.text
                            setStreamingText(fullText)
                        }
                        if (parsed.done) {
                            console.log('SSE done event - sources:', parsed.sources) // Debug log
                            finalMetadata = {
                                citations: parsed.citations,
                                sources: parsed.sources
                            }
                        }
                    } catch (e) {
                        // Skip unparseable
                    }
                }
            }

            // Add assistant message
            const assistantMessage: Message = {
                role: 'assistant',
                content: fullText,
                timestamp: Date.now(),
                citations: finalMetadata.citations,
                sources: finalMetadata.sources
            }

            setMessages(prev => [...prev, assistantMessage])

        } catch (e) {
            console.error('Chat error:', e)
            setError('Failed to send message. Please try again.')
        } finally {
            setIsStreaming(false)
            setStreamingText('')
        }
    }

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            sendMessage()
        }
    }

    // Parse and render message with clickable citations
    const renderMessageContent = (content: string) => {
        // Pattern: [Case Name](doc:case_id)
        const parts = content.split(/(\[[^\]]+\]\(doc:[^)]+\))/g)

        return parts.map((part, index) => {
            const match = part.match(/\[([^\]]+)\]\(doc:([^)]+)\)/)
            if (match) {
                const [, title, docId] = match
                return (
                    <button
                        key={index}
                        className="citation-link"
                        onClick={() => onViewDocument?.(docId, title)}
                        title={`View: ${title}`}
                    >
                        📄 {title}
                    </button>
                )
            }
            return <span key={index}>{part}</span>
        })
    }

    const clearHistory = () => {
        setMessages([])
        localStorage.removeItem(`chat_history_${sessionId.current}`)
    }

    return (
        <div className="chat-interface">
            <div className="chat-header">
                <h2>⚖️ Legal Lens AI</h2>
                <span className="session-badge">Session: {sessionId.current.slice(-6)}</span>
                {messages.length > 0 && (
                    <button className="clear-btn" onClick={clearHistory}>
                        Clear History
                    </button>
                )}
            </div>

            <div className="chat-messages">
                {messages.length === 0 && !isStreaming && (
                    <div className="welcome-message">
                        <h3>Welcome to Legal Lens AI</h3>
                        <p>Ask me anything about Indian law, IPC/BNS mappings, or landmark cases.</p>
                        <div className="example-queries">
                            <strong>Try asking:</strong>
                            <ul>
                                <li>"What is the Right to Privacy case about?"</li>
                                <li>"Explain IPC Section 377"</li>
                                <li>"What are the Vishaka Guidelines?"</li>
                                <li>"What is the punishment for murder under BNS?"</li>
                            </ul>
                        </div>
                    </div>
                )}

                {messages.map((msg, idx) => (
                    <div key={idx} className={`message ${msg.role}`}>
                        <div className="message-avatar">
                            {msg.role === 'user' ? '👤' : '⚖️'}
                        </div>
                        <div className="message-content">
                            {msg.role === 'assistant'
                                ? renderMessageContent(msg.content)
                                : msg.content
                            }
                            {msg.sources && msg.sources.length > 0 && (
                                <div className="message-sources">
                                    <span className="sources-label">Sources:</span>
                                    {msg.sources.map((s, i) => (
                                        <button
                                            key={i}
                                            className="source-chip"
                                            onClick={() => onViewDocument?.(s.docId)}
                                        >
                                            {s.title.split('(')[0].trim()}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                ))}

                {isStreaming && (
                    <div className="message assistant streaming">
                        <div className="message-avatar">⚖️</div>
                        <div className="message-content">
                            {renderMessageContent(streamingText)}
                            <span className="cursor-blink">▋</span>
                        </div>
                    </div>
                )}

                {error && (
                    <div className="error-message">
                        ⚠️ {error}
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            <div className="chat-input-area">
                <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Ask about Indian law, cases, or statutes..."
                    disabled={isStreaming}
                    rows={2}
                />
                <button
                    className="send-btn"
                    onClick={sendMessage}
                    disabled={!input.trim() || isStreaming}
                >
                    {isStreaming ? '...' : '➤'}
                </button>
            </div>
        </div>
    )
}
