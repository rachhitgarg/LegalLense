import { useEffect, useState } from 'react'
import './DocumentViewer.css'

interface Document {
    doc_id: string
    title: string
    content: string
    jurisdiction?: string
    year?: string
    keywords?: string[]
}

interface DocumentViewerProps {
    docId: string
    highlight?: string
    onClose: () => void
}

export default function DocumentViewer({ docId, highlight, onClose }: DocumentViewerProps) {
    const [document, setDocument] = useState<Document | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        fetchDocument()
    }, [docId])

    const fetchDocument = async () => {
        setLoading(true)
        setError(null)

        try {
            // Fetch document directly by ID
            const API_URL = import.meta.env.DEV ? 'http://localhost:8888/api' : '/api'
            const response = await fetch(`${API_URL}/document/${docId}`)

            if (!response.ok) {
                if (response.status === 404) {
                    setError('Document not found')
                } else {
                    throw new Error('Failed to fetch document')
                }
                return
            }

            const doc = await response.json()
            setDocument(doc)
        } catch (e) {
            setError('Failed to load document')
            console.error(e)
        } finally {
            setLoading(false)
        }
    }

    // Highlight text in content
    const renderContent = (content: string) => {
        if (!highlight) return content

        const regex = new RegExp(`(${highlight})`, 'gi')
        const parts = content.split(regex)

        return parts.map((part, index) => {
            if (part.toLowerCase() === highlight.toLowerCase()) {
                return (
                    <mark key={index} className="highlight">
                        {part}
                    </mark>
                )
            }
            return part
        })
    }

    return (
        <div className="document-viewer-overlay" onClick={onClose}>
            <div className="document-viewer" onClick={e => e.stopPropagation()}>
                <div className="document-header">
                    <h2>{document?.title || 'Loading...'}</h2>
                    <button className="close-btn" onClick={onClose}>✕</button>
                </div>

                {loading && (
                    <div className="loading-state">
                        <div className="spinner"></div>
                        <p>Loading document...</p>
                    </div>
                )}

                {error && (
                    <div className="error-state">
                        <p>⚠️ {error}</p>
                    </div>
                )}

                {document && !loading && (
                    <div className="document-body">
                        <div className="document-meta">
                            <span className="meta-item">
                                📅 {document.year || 'Unknown year'}
                            </span>
                            <span className="meta-item">
                                🏛️ {document.jurisdiction || 'Supreme Court'}
                            </span>
                            {document.keywords && (
                                <div className="keywords">
                                    {document.keywords.slice(0, 5).map((kw, i) => (
                                        <span key={i} className="keyword-tag">{kw}</span>
                                    ))}
                                </div>
                            )}
                        </div>

                        <div className="document-content">
                            {renderContent(document.content)}
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
