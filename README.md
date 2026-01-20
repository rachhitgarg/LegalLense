# Legal Lens 🔍⚖️

**AI-powered contextual search engine for Indian legal documents**

## Features

- 🔍 **Semantic Search** - BGE-M3 embeddings for multilingual legal document search
- 🧠 **Knowledge Graph** - Neo4j graph database for IPC↔BNS statute mapping
- 🤖 **AI Summaries** - OpenAI-powered case summaries and answers
- ⚡ **Vector Database** - Qdrant Cloud for fast similarity search
- 🎨 **Modern UI** - React + Vite with light/dark mode

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Qdrant Cloud account
- Neo4j Aura account (or local Neo4j)
- OpenAI API key

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
cp ../.env.example .env
# Edit .env with your credentials
python -m uvicorn api.main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Environment Variables

Create a `.env` file in the backend folder:

```env
QDRANT_CLOUD_URL=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=your-api-key
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
OPENAI_API_KEY=sk-your-key
JWT_SECRET=your-secret
```

## Project Structure

```
LegalLensProject/
├── backend/
│   ├── api/           # FastAPI endpoints
│   ├── pipeline/      # Data ingestion & embeddings
│   ├── llm/           # OpenAI integration
│   ├── retrieval/     # Fusion search
│   └── utils/         # Logging
├── frontend/
│   └── src/           # React components
├── data/              # Judgment PDFs & mapping.json
├── tests/             # Unit & integration tests
├── render.yaml        # Render.com deployment
└── docker-compose.yml # Local development
```

## Demo Credentials

- Username: `practitioner_demo`
- Password: `demo123`

## Deployment

### Render.com (Recommended)

1. Push to GitHub
2. Connect repo to Render
3. Render auto-detects `render.yaml`
4. Add environment variables in Render dashboard

## License

Educational use only. Not for legal advice.

## Disclaimer

⚠️ This is an educational research tool. It does not provide legal advice. Always consult a qualified lawyer for legal decisions.
