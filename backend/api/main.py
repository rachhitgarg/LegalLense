"""
main.py - FastAPI application for Legal Lens.

Endpoints:
- POST /search         - Search legal documents
- POST /login          - Authenticate and get JWT
- GET  /history        - Get conversation history
- POST /admin/mapping  - Upload mapping file (practitioner only)
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from .auth import (
    User,
    TokenPayload,
    create_token,
    authenticate_demo,
    get_current_user,
    require_practitioner,
    require_student_or_practitioner,
)

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Legal Lens API",
    description="LLM-powered contextual search engine for Indian legal documents",
    version="0.1.0",
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "https://legal-lens-frontend.onrender.com",
        "https://legallense-h1fh.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory for session logs
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Request/Response Models
# ─────────────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10


class SearchResult(BaseModel):
    doc_id: str
    content: str
    score: float
    source: str


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    llm_response: str
    timestamp: str


class HistoryEntry(BaseModel):
    query: str
    response: str
    timestamp: str


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Legal Lens API"}


@app.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate and return JWT token."""
    user = authenticate_demo(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token(user)
    return LoginResponse(access_token=token, role=user.role)


@app.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    user: TokenPayload = Depends(require_student_or_practitioner),
):
    """
    Search legal documents using fusion retrieval + LLM.
    
    Requires authentication (practitioner or student).
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from pipeline.embeddings import EmbeddingService
    from llm.online_client import OnlineLLMClient
    
    timestamp = datetime.utcnow().isoformat()
    
    # Get Qdrant credentials
    cloud_url = os.getenv("QDRANT_CLOUD_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    
    results = []
    llm_response = ""
    
    try:
        # Initialize embedding service
        embedding_service = EmbeddingService(
            cloud_url=cloud_url,
            api_key=api_key,
            model_name="BAAI/bge-m3"
        )
        
        # Search Qdrant
        search_results = embedding_service.search(request.query, top_k=request.top_k)
        
        for r in search_results:
            results.append(SearchResult(
                doc_id=r["payload"].get("doc_id", str(r["id"])),
                content=r["payload"].get("content_preview", "")[:500],
                score=r["score"],
                source="vector",
            ))
        
        # Build context for LLM
        context = "\n\n".join([
            f"Document: {r.doc_id}\n{r.content}"
            for r in results[:5]
        ])
        
        # Generate LLM response
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if openai_key and not openai_key.startswith("YOUR_"):
            try:
                llm_client = OnlineLLMClient(api_key=openai_key)
                llm_response = llm_client.generate(request.query, context)
            except Exception as e:
                llm_response = f"LLM error: {str(e)}"
        else:
            llm_response = "Set your OPENAI_API_KEY in .env for AI-powered summaries."
            
    except Exception as e:
        # Fallback to placeholder if services unavailable
        results = [SearchResult(
            doc_id="error",
            content=f"Search error: {str(e)}",
            score=0.0,
            source="error",
        )]
        llm_response = f"Error connecting to search services: {str(e)}"
    
    # Log the search
    _save_to_history(user.sub, request.query, llm_response, timestamp)
    
    return SearchResponse(
        query=request.query,
        results=results,
        llm_response=llm_response,
        timestamp=timestamp,
    )


@app.get("/history", response_model=list[HistoryEntry])
async def get_history(
    user: TokenPayload = Depends(get_current_user),
    limit: int = 50,
):
    """Get conversation history for the current user."""
    history_file = LOGS_DIR / f"history_{user.sub}.json"
    
    if not history_file.exists():
        return []
    
    with open(history_file, "r", encoding="utf-8") as f:
        entries = json.load(f)
    
    return entries[-limit:]


@app.post("/admin/mapping")
async def upload_mapping(
    file: UploadFile = File(...),
    user: TokenPayload = Depends(require_practitioner),
):
    """
    Upload a new IPC↔BNS mapping file (JSON).
    
    Requires practitioner role.
    """
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only JSON files are supported")
    
    content = await file.read()
    
    # Validate JSON
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    
    # Save to data folder
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    mapping_path = data_dir / "mapping.json"
    
    with open(mapping_path, "wb") as f:
        f.write(content)
    
    # TODO: Reload mapping into Neo4j
    
    return {"message": "Mapping uploaded successfully", "entries": len(data)}


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

def _save_to_history(user_id: str, query: str, response: str, timestamp: str):
    """Append a search to the user's history file."""
    history_file = LOGS_DIR / f"history_{user_id}.json"
    
    entries = []
    if history_file.exists():
        with open(history_file, "r", encoding="utf-8") as f:
            entries = json.load(f)
    
    entries.append({
        "query": query,
        "response": response,
        "timestamp": timestamp,
    })
    
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
