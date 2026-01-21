import { useState, useEffect } from 'react'
import './App.css'

// API URL - use /api prefix which Vercel will proxy to backend
const API_URL = '/api'

interface SearchResult {
    doc_id: string
    content: string
    score: number
    source: string
}

interface SearchResponse {
    query: string
    results: SearchResult[]
    llm_response: string
    timestamp: string
}

function App() {
    const [query, setQuery] = useState('')
    const [results, setResults] = useState<SearchResponse | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [darkMode, setDarkMode] = useState(false)
    const [token, setToken] = useState<string | null>(null)

    useEffect(() => {
        // Check for saved theme preference
        const savedTheme = localStorage.getItem('theme')
        if (savedTheme === 'dark') {
            setDarkMode(true)
            document.documentElement.setAttribute('data-theme', 'dark')
        }

        // Check for saved token
        const savedToken = localStorage.getItem('token')
        if (savedToken) {
            setToken(savedToken)
        }
    }, [])

    const toggleDarkMode = () => {
        const newMode = !darkMode
        setDarkMode(newMode)
        document.documentElement.setAttribute('data-theme', newMode ? 'dark' : 'light')
        localStorage.setItem('theme', newMode ? 'dark' : 'light')
    }

    const handleLogin = async (username: string, password: string) => {
        try {
            const response = await fetch(`${API_URL}/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password }),
            })

            if (!response.ok) {
                throw new Error('Login failed')
            }

            const data = await response.json()
            setToken(data.access_token)
            localStorage.setItem('token', data.access_token)
        } catch (err) {
            setError('Login failed. Please check your credentials.')
        }
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
                    'Authorization': `Bearer ${token}`,
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
                {/* Login Section (if not authenticated) */}
                {!token && (
                    <div className="login-card">
                        <h2>Login</h2>
                        <p>Demo credentials: practitioner_demo / demo123</p>
                        <div className="login-form">
                            <input
                                type="text"
                                id="username"
                                placeholder="Username"
                                className="input"
                            />
                            <input
                                type="password"
                                id="password"
                                placeholder="Password"
                                className="input"
                            />
                            <button
                                className="btn btn-primary"
                                onClick={() => {
                                    const username = (document.getElementById('username') as HTMLInputElement).value
                                    const password = (document.getElementById('password') as HTMLInputElement).value
                                    handleLogin(username, password)
                                }}
                            >
                                Login
                            </button>
                        </div>
                    </div>
                )}

                {/* Search Section */}
                {token && (
                    <>
                        <div className="search-section">
                            <div className="search-box">
                                <input
                                    type="text"
                                    className="search-input"
                                    placeholder="Search legal documents (e.g., 'medical negligence cases')"
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
                                {/* LLM Response */}
                                <div className="llm-response">
                                    <h3>AI Summary</h3>
                                    <p>{results.llm_response}</p>
                                </div>

                                {/* Retrieved Documents */}
                                <div className="documents">
                                    <h3>Retrieved Documents</h3>
                                    {results.results.map((result, index) => (
                                        <div key={index} className="document-card">
                                            <div className="document-header">
                                                <span className="doc-id">{result.doc_id}</span>
                                                <span className="doc-source">{result.source}</span>
                                                <span className="doc-score">{(result.score * 100).toFixed(1)}%</span>
                                            </div>
                                            <p className="doc-content">{result.content}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </>
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
