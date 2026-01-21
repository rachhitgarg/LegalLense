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

# CORS middleware for frontend - allow all origins for cloud deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Must be False when using "*"
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
    Search legal documents using Qdrant + LLM (Groq or OpenAI).
    """
    import httpx
    from qdrant_client import QdrantClient
    
    timestamp = datetime.utcnow().isoformat()
    
    # Get credentials
    cloud_url = os.getenv("QDRANT_CLOUD_URL")
    qdrant_key = os.getenv("QDRANT_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY", "")
    openai_key = os.getenv("OPENAI_API_KEY", "")
    
    results = []
    llm_response = ""
    
    try:
        # Connect to Qdrant Cloud
        qdrant = QdrantClient(url=cloud_url, api_key=qdrant_key)
        
        # Get collection info to check vector size
        collection = qdrant.get_collection("legal_documents")
        vector_size = collection.config.params.vectors.size
        
        # Use appropriate model based on collection vector size
        if vector_size == 1024:
            from FlagEmbedding import BGEM3FlagModel
            model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
            embeddings = model.encode([request.query])
            query_vector = embeddings["dense_vecs"][0].tolist()
        else:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer("all-MiniLM-L6-v2")
            query_vector = model.encode(request.query).tolist()
        
        # Search Qdrant
        search_results = qdrant.search(
            collection_name="legal_documents",
            query_vector=query_vector,
            limit=request.top_k,
        )
        
        for r in search_results:
            results.append(SearchResult(
                doc_id=r.payload.get("doc_id", r.payload.get("filename", str(r.id))),
                content=r.payload.get("content_preview", r.payload.get("content", ""))[:500],
                score=r.score,
                source="vector",
            ))
        
        # Build context for LLM
        context = "\n\n".join([
            f"Document: {r.doc_id}\n{r.content}"
            for r in results[:3]
        ])
        
        # Try Groq first (faster), then OpenAI
        if groq_key:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {groq_key}"},
                        json={
                            "model": "llama-3.1-8b-instant",
                            "messages": [
                                {"role": "system", "content": "You are a legal research assistant. Provide concise summaries."},
                                {"role": "user", "content": f"Query: {request.query}\n\nDocuments:\n{context}"}
                            ],
                            "max_tokens": 500
                        },
                        timeout=30.0
                    )
                    data = response.json()
                    llm_response = data["choices"][0]["message"]["content"]
            except Exception as e:
                llm_response = f"Groq error: {str(e)}"
        elif openai_key and not openai_key.startswith("YOUR_"):
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a legal research assistant."},
                    {"role": "user", "content": f"Query: {request.query}\n\nDocuments:\n{context}"}
                ],
                max_tokens=500
            )
            llm_response = response.choices[0].message.content
        else:
            llm_response = "Set GROQ_API_KEY or OPENAI_API_KEY for AI summaries."
            
    except Exception as e:
        # Return error with details
        import traceback
        error_details = f"{str(e)}\n{traceback.format_exc()}"
        results = [SearchResult(
            doc_id="error",
            content=f"Search error: {str(e)[:200]}",
            score=0.0,
            source="error",
        )]
        llm_response = f"Error: {str(e)[:300]}"
    
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
