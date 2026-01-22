"""
FastAPI Application for Legal Lens

Endpoints:
- GET / - Health check
- POST /search - Search with KG + documents + LightRAG
- GET /statute/{code}/{section} - Statute mapping lookup
- POST /lightrag/query - Direct LightRAG query
- POST /lightrag/index - Index documents into LightRAG
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from contextlib import asynccontextmanager
import os
import sys

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.knowledge_graph import get_knowledge_graph
from core.search import get_search_engine
from core.lightrag_engine import get_lightrag_engine, HAS_LIGHTRAG


# Lifespan for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize LightRAG
    if HAS_LIGHTRAG:
        engine = get_lightrag_engine()
        try:
            await engine.initialize()
            print("LightRAG initialized at startup")
        except Exception as e:
            print(f"LightRAG init failed: {e}")
    yield
    # Shutdown: Cleanup
    if HAS_LIGHTRAG:
        engine = get_lightrag_engine()
        await engine.finalize()


# Initialize FastAPI
app = FastAPI(
    title="Legal Lens API",
    description="AI-powered search for Indian legal documents with KG + LightRAG",
    version="2.0.0",
    lifespan=lifespan
)

# CORS - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    use_lightrag: Optional[bool] = True  # Enable LightRAG by default


class LightRAGQueryRequest(BaseModel):
    query: str
    mode: Optional[str] = "hybrid"  # naive, local, global, hybrid
    top_k: Optional[int] = 5


class SearchResponse(BaseModel):
    query: str
    statute_mapping: Optional[dict]
    related_statutes: List[dict]
    kg_concepts: List[dict]
    results: List[dict]
    total_results: int
    lightrag_answer: Optional[str] = None  # LightRAG response


# Endpoints
@app.get("/")
async def health_check():
    """API health check."""
    kg = get_knowledge_graph()
    lightrag_engine = get_lightrag_engine()
    
    return {
        "status": "ok",
        "service": "Legal Lens API",
        "version": "2.0.0",
        "kg_nodes": len(kg.nodes),
        "kg_edges": len(kg.edges),
        "lightrag_available": HAS_LIGHTRAG,
        "lightrag_status": lightrag_engine.get_status()
    }


@app.post("/search")
async def search(request: SearchRequest):
    """
    Search for legal documents using KG + keyword search + LightRAG.
    
    Returns matching documents with:
    - Statute mappings (if query contains IPC/CrPC references)
    - Related concepts from Knowledge Graph
    - Ranked document results
    - LightRAG AI answer (if enabled)
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # 1. KG + Document Search
    engine = get_search_engine()
    results = engine.search(request.query, top_k=request.top_k)
    
    # 2. LightRAG Query (if available and enabled)
    lightrag_answer = None
    if request.use_lightrag and HAS_LIGHTRAG:
        try:
            lightrag_engine = get_lightrag_engine()
            if lightrag_engine.is_initialized:
                rag_result = await lightrag_engine.query(
                    request.query, 
                    mode="hybrid",
                    top_k=request.top_k
                )
                if not rag_result.get("error"):
                    lightrag_answer = rag_result.get("answer")
        except Exception as e:
            print(f"LightRAG query error: {e}")
    
    # Combine results
    return {
        **results,
        "lightrag_answer": lightrag_answer
    }


@app.post("/lightrag/query")
async def lightrag_query(request: LightRAGQueryRequest):
    """
    Direct LightRAG query endpoint.
    
    Modes:
    - naive: Simple vector search
    - local: Entity-focused retrieval
    - global: High-level summaries
    - hybrid: Combination of local and global
    """
    if not HAS_LIGHTRAG:
        raise HTTPException(status_code=503, detail="LightRAG not available")
    
    lightrag_engine = get_lightrag_engine()
    
    if not lightrag_engine.is_initialized:
        try:
            await lightrag_engine.initialize()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to init LightRAG: {e}")
    
    result = await lightrag_engine.query(
        request.query,
        mode=request.mode,
        top_k=request.top_k
    )
    
    return result


@app.post("/lightrag/index")
async def lightrag_index(background_tasks: BackgroundTasks, force: bool = False):
    """
    Index documents into LightRAG.
    
    This runs in the background as it may take time.
    """
    if not HAS_LIGHTRAG:
        raise HTTPException(status_code=503, detail="LightRAG not available")
    
    lightrag_engine = get_lightrag_engine()
    
    # Run indexing in background
    async def do_index():
        await lightrag_engine.index_documents(force_reindex=force)
    
    background_tasks.add_task(do_index)
    
    return {
        "status": "indexing_started",
        "force_reindex": force,
        "documents_count": len(lightrag_engine.documents)
    }


@app.get("/lightrag/status")
async def lightrag_status():
    """Get LightRAG status."""
    if not HAS_LIGHTRAG:
        return {"available": False, "error": "LightRAG not installed"}
    
    return get_lightrag_engine().get_status()


@app.get("/statute/{code}/{section}")
async def get_statute_mapping(code: str, section: str):
    """
    Get statute mapping for old code to new code.
    
    Examples:
    - /statute/IPC/302 → BNS 103
    - /statute/IPC/377 → BNS None (decriminalized)
    """
    kg = get_knowledge_graph()
    mapping = kg.get_statute_mapping(code.upper(), section)
    
    if not mapping:
        raise HTTPException(
            status_code=404, 
            detail=f"No mapping found for {code} Section {section}"
        )
    
    return mapping


@app.get("/judgments/citing/{code}/{section}")
async def get_judgments_citing_statute(code: str, section: str):
    """Get all judgments that cite a specific statute."""
    kg = get_knowledge_graph()
    judgments = kg.find_judgments_citing_statute(code.upper(), section)
    
    return {
        "statute": f"{code} {section}",
        "judgments": [
            {"id": j["id"], "title": j.get("title", ""), "year": j.get("year")}
            for j in judgments
        ],
        "count": len(judgments)
    }


@app.get("/concepts/{concept_id}")
async def get_concept_judgments(concept_id: str):
    """Get judgments that interpret a specific concept."""
    kg = get_knowledge_graph()
    judgments = kg.find_related_judgments(concept_id)
    
    return {
        "concept": concept_id,
        "judgments": [
            {"id": j["id"], "title": j.get("title", ""), "year": j.get("year")}
            for j in judgments
        ],
        "count": len(judgments)
    }


@app.get("/kg/stats")
async def kg_stats():
    """Get Knowledge Graph statistics."""
    kg = get_knowledge_graph()
    
    judgments = kg.get_all_judgments()
    statutes = kg.get_all_statutes()
    concepts = kg.get_all_concepts()
    
    return {
        "total_nodes": len(kg.nodes),
        "total_edges": len(kg.edges),
        "judgments": len(judgments),
        "statutes": len(statutes),
        "concepts": len(concepts)
    }


# Run with: uvicorn app:app --reload --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
