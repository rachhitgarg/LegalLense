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
    Search legal documents using local search + LLM (Groq or OpenAI).
    
    No external vector database required!
    """
    import httpx
    import sys
    from pathlib import Path
    
    # Add parent to path for imports
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from pipeline.faiss_search import get_search_engine
    from pipeline.graph_local import get_knowledge_graph
    
    timestamp = datetime.utcnow().isoformat()
    
    # Get LLM credentials
    groq_key = os.getenv("GROQ_API_KEY", "")
    openai_key = os.getenv("OPENAI_API_KEY", "")
    
    results = []
    llm_response = ""
    
    try:
        # Use local search engine
        search_engine = get_search_engine()
        search_results = search_engine.search(request.query, top_k=request.top_k)
        
        for r in search_results:
            results.append(SearchResult(
                doc_id=r.doc_id,
                content=r.content,
                score=r.score,
                source=r.source,
            ))
        
        # Check for statute references in query
        kg = get_knowledge_graph()
        statute_info = ""
        
        # Look for IPC/BNS section references in query
        import re
        ipc_match = re.search(r'(IPC|ipc)\s*(\d+)', request.query)
        bns_match = re.search(r'(BNS|bns)\s*(\d+)', request.query)
        
        if ipc_match:
            section = ipc_match.group(2)
            mapping = kg.get_mapping("IPC", section)
            if mapping:
                statute_info = f"\n\nStatute Mapping: {mapping['mapping']}"
        elif bns_match:
            section = bns_match.group(2)
            # Search for BNS to find corresponding IPC
            statute_results = kg.search_statutes(f"BNS {section}")
            if statute_results:
                statute_info = f"\n\nRelated statute: {statute_results[0]}"
        
        # Build context for LLM
        context = "\n\n".join([
            f"Document: {r.doc_id}\n{r.content}"
            for r in results[:3]
        ])
        context += statute_info
        
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
                                {"role": "system", "content": "You are a legal research assistant for Indian law. Provide concise, accurate summaries based on the documents provided. If statute mappings are shown, explain the correspondence between old (IPC/CrPC) and new (BNS/BNSS) laws."},
                                {"role": "user", "content": f"Query: {request.query}\n\nDocuments:\n{context}"}
                            ],
                            "max_tokens": 500
                        },
                        timeout=30.0
                    )
                    data = response.json()
                    if "choices" in data:
                        llm_response = data["choices"][0]["message"]["content"]
                    else:
                        llm_response = f"Groq API response: {data.get('error', {}).get('message', str(data))}"
            except Exception as e:
                llm_response = f"Groq error: {str(e)}"
        elif openai_key and not openai_key.startswith("YOUR_"):
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a legal research assistant for Indian law."},
                    {"role": "user", "content": f"Query: {request.query}\n\nDocuments:\n{context}"}
                ],
                max_tokens=500
            )
            llm_response = response.choices[0].message.content
        else:
            # No LLM - just return search results
            llm_response = f"Found {len(results)} relevant documents. Set GROQ_API_KEY for AI-powered summaries."
            
    except Exception as e:
        import traceback
        error_msg = str(e)
        results = [SearchResult(
            doc_id="error",
            content=f"Search error: {error_msg[:300]}",
            score=0.0,
            source="error",
        )]
        llm_response = f"Error: {error_msg[:200]}"
    
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
