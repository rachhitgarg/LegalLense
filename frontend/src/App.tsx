import { useState, useEffect } from 'react'
import './App.css'

// API URL - local dev uses localhost, production uses /api (Netlify redirect)
const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : '/api'

interface SearchResult {
    doc_id: string
    title: string
    content: string
    score: number
    year?: number
    court: string
    statutes: string[]
    keywords: string[]
}

interface StatuteMapping {
    old_code: string
    old_section: string
    new_code: string
    new_section: string
    title: string
}

interface KgConcept {
    id: string
    name: string
}

interface SearchResponse {
    query: string
    statute_mapping: StatuteMapping | null
    related_statutes: Array<{ id: string; title: string }>
    kg_concepts: KgConcept[]
    results: SearchResult[]
    total_results: number
    lightrag_answer?: string  // AI-generated answer from LightRAG
}

function App() {
    const [query, setQuery] = useState('')
    const [results, setResults] = useState<SearchResponse | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [darkMode, setDarkMode] = useState(false)

    useEffect(() => {
        // Check for saved theme preference
        const savedTheme = localStorage.getItem('theme')
        if (savedTheme === 'dark') {
            setDarkMode(true)
            document.documentElement.setAttribute('data-theme', 'dark')
        }
    }, [])

    const toggleDarkMode = () => {
        const newMode = !darkMode
        setDarkMode(newMode)
        document.documentElement.setAttribute('data-theme', newMode ? 'dark' : 'light')
        localStorage.setItem('theme', newMode ? 'dark' : 'light')
    }

    const handleSearch = async () => {
        if (!query.trim()) return

        setLoading(true)
        setError(null)

        try {
            const response = await fetch(`${API_URL}/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query, top_k: 10 }),
            })

            if (!response.ok) {
                throw new Error('Search failed')
            }

            const data = await response.json()
            setResults(data)
        } catch (err) {
            setError('Search failed. Please try again.')
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            handleSearch()
        }
    }

    return (
        <div className="app">
            {/* Header */}
            <header className="header">
                <div className="header-content">
                    <h1 className="logo">⚖️ Legal Lens</h1>
                    <p className="tagline">AI-powered search for Indian legal documents</p>
                </div>
                <button className="theme-toggle" onClick={toggleDarkMode}>
                    {darkMode ? '☀️' : '🌙'}
                </button>
            </header>

            {/* Main Content */}
            <main className="main">
                {/* Search Section */}
                <div className="search-section">
                    <div className="search-box">
                        <input
                            type="text"
                            className="search-input"
                            placeholder="Search legal documents (e.g., 'IPC 377', 'medical negligence', 'right to privacy')"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            onKeyPress={handleKeyPress}
                        />
                        <button
                            className="btn btn-primary search-btn"
                            onClick={handleSearch}
                            disabled={loading}
                        >
                            {loading ? 'Searching...' : 'Search'}
                        </button>
                    </div>
                </div>

                {/* Error Message */}
                {error && (
                    <div className="error-message">
                        {error}
                    </div>
                )}

                {/* Results Section */}
                {results && (
                    <div className="results-section">
                        {/* Statute Mapping (if found) */}
                        {results.statute_mapping && (
                            <div className="statute-mapping">
                                <h3>📜 Statute Mapping</h3>
                                <div className="mapping-card">
                                    <span className="old-statute">
                                        {results.statute_mapping.old_code} Section {results.statute_mapping.old_section}
                                    </span>
                                    <span className="arrow">→</span>
                                    <span className="new-statute">
                                        {results.statute_mapping.new_code} Section {results.statute_mapping.new_section}
                                    </span>
                                    <p className="mapping-title">{results.statute_mapping.title}</p>
                                </div>
                            </div>
                        )}

                        {/* AI Answer from LightRAG */}
                        {results.lightrag_answer && (
                            <div className="ai-answer">
                                <h3>🤖 AI Answer</h3>
                                <div className="ai-answer-content">
                                    <p>{results.lightrag_answer}</p>
                                </div>
                            </div>
                        )}

                        {/* KG Concepts */}
                        {results.kg_concepts.length > 0 && (
                            <div className="kg-concepts">
                                <h4>🔗 Related Concepts</h4>
                                <div className="concept-tags">
                                    {results.kg_concepts.map((concept) => (
                                        <span key={concept.id} className="concept-tag">
                                            {concept.name || concept.id}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Retrieved Documents */}
                        <div className="documents">
                            <h3>📚 Retrieved Documents ({results.total_results})</h3>
                            {results.results.length === 0 ? (
                                <p className="no-results">No documents found. Try a different query.</p>
                            ) : (
                                results.results.map((result, index) => (
                                    <div key={index} className="document-card">
                                        <div className="document-header">
                                            <h4 className="doc-title">{result.title}</h4>
                                            <span className="doc-score">{(result.score * 100).toFixed(0)}% match</span>
                                        </div>
                                        <div className="doc-meta">
                                            {result.year && <span className="doc-year">{result.year}</span>}
                                            {result.court && <span className="doc-court">{result.court}</span>}
                                        </div>
                                        <p className="doc-content">{result.content}</p>
                                        {result.statutes.length > 0 && (
                                            <div className="doc-statutes">
                                                {result.statutes.map((s, i) => (
                                                    <span key={i} className="statute-tag">{s}</span>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                )}
            </main>

            {/* Footer */}
            <footer className="footer">
                <p>
                    ⚠️ This is an educational tool, not legal advice. Consult a qualified lawyer for legal decisions.
                </p>
            </footer>
        </div>
    )
}

export default App
