"""
LightRAG Engine for Legal Lens

Provides graph-enhanced RAG capabilities:
- Automatic entity extraction from documents
- Dual-level retrieval (entity + multi-hop)
- Integration with Knowledge Graph
"""

import os
import asyncio
import json
from typing import List, Dict, Optional, Any
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Check if LightRAG is available
try:
    from lightrag import LightRAG, QueryParam
    from lightrag.utils import setup_logger
    HAS_LIGHTRAG = True
except ImportError:
    HAS_LIGHTRAG = False
    print("Warning: LightRAG not installed. Run: pip install lightrag-hku")


class LightRAGEngine:
    """
    LightRAG Engine wrapper for Legal Lens.
    
    Provides semantic search + entity extraction over judgment documents.
    """
    
    def __init__(
        self, 
        working_dir: Optional[str] = None,
        documents_path: Optional[str] = None,
        use_openai: bool = True
    ):
        """
        Initialize LightRAG Engine.
        
        Args:
            working_dir: Directory for LightRAG storage
            documents_path: Path to documents.json
            use_openai: Use OpenAI embeddings (requires OPENAI_API_KEY)
        """
        base_dir = Path(__file__).parent.parent
        
        self.working_dir = working_dir or str(base_dir / "lightrag_storage")
        self.documents_path = documents_path or str(base_dir / "data" / "documents.json")
        self.use_openai = use_openai
        
        self.rag: Optional[LightRAG] = None
        self.is_initialized = False
        self.documents: List[Dict] = []
        
        # Create working directory
        os.makedirs(self.working_dir, exist_ok=True)
        
        # Load documents
        self._load_documents()
    
    def _load_documents(self):
        """Load judgment documents."""
        if os.path.exists(self.documents_path):
            with open(self.documents_path, 'r', encoding='utf-8') as f:
                self.documents = json.load(f)
            print(f"Loaded {len(self.documents)} documents for LightRAG")
    
    async def initialize(self):
        """Initialize LightRAG instance."""
        if not HAS_LIGHTRAG:
            print("LightRAG not available")
            return False
        
        try:
            # Import LLM functions based on configuration
            if self.use_openai:
                from lightrag.llm.openai import openai_embed, gpt_4o_mini_complete
                
                self.rag = LightRAG(
                    working_dir=self.working_dir,
                    embedding_func=openai_embed,
                    llm_model_func=gpt_4o_mini_complete,
                )
            else:
                # Use default/local model
                self.rag = LightRAG(
                    working_dir=self.working_dir,
                )
            
            # Initialize storages
            await self.rag.initialize_storages()
            self.is_initialized = True
            print("LightRAG initialized successfully")
            return True
            
        except Exception as e:
            print(f"Failed to initialize LightRAG: {e}")
            return False
    
    async def index_documents(self, force_reindex: bool = False):
        """
        Index all documents into LightRAG.
        
        Args:
            force_reindex: Force reindexing even if already done
        """
        if not self.is_initialized:
            await self.initialize()
        
        if not self.rag:
            print("LightRAG not available")
            return
        
        # Check if already indexed (simple check)
        index_marker = Path(self.working_dir) / ".indexed"
        if index_marker.exists() and not force_reindex:
            print("Documents already indexed. Use force_reindex=True to reindex.")
            return
        
        print(f"Indexing {len(self.documents)} documents...")
        
        for doc in self.documents:
            # Prepare document text
            text = self._format_document_for_indexing(doc)
            
            try:
                await self.rag.ainsert(text)
                print(f"  Indexed: {doc.get('doc_id', 'unknown')}")
            except Exception as e:
                print(f"  Error indexing {doc.get('doc_id')}: {e}")
        
        # Mark as indexed
        index_marker.write_text("indexed")
        print("Indexing complete!")
    
    def _format_document_for_indexing(self, doc: Dict) -> str:
        """Format a document for LightRAG indexing."""
        parts = []
        
        if doc.get("title"):
            parts.append(f"Title: {doc['title']}")
        
        if doc.get("year"):
            parts.append(f"Year: {doc['year']}")
        
        if doc.get("court"):
            parts.append(f"Court: {doc['court']}")
        
        if doc.get("statutes"):
            parts.append(f"Statutes: {', '.join(doc['statutes'])}")
        
        if doc.get("keywords"):
            parts.append(f"Keywords: {', '.join(doc['keywords'])}")
        
        if doc.get("content"):
            parts.append(f"\n{doc['content']}")
        
        return "\n".join(parts)
    
    async def query(
        self, 
        query: str, 
        mode: str = "hybrid",
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Query LightRAG for relevant documents.
        
        Args:
            query: User query
            mode: Query mode - "naive", "local", "global", "hybrid"
            top_k: Number of results
        
        Returns:
            Query results with answer and sources
        """
        if not self.is_initialized:
            await self.initialize()
        
        if not self.rag:
            return {
                "answer": "LightRAG not available",
                "mode": mode,
                "error": True
            }
        
        try:
            # Execute query
            result = await self.rag.aquery(
                query,
                param=QueryParam(mode=mode, top_k=top_k)
            )
            
            return {
                "answer": result,
                "mode": mode,
                "query": query,
                "error": False
            }
            
        except Exception as e:
            return {
                "answer": f"Query error: {str(e)}",
                "mode": mode,
                "error": True
            }
    
    async def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Search for relevant documents using hybrid mode.
        
        This is a simplified interface that just returns the answer.
        """
        result = await self.query(query, mode="hybrid", top_k=top_k)
        return result
    
    async def finalize(self):
        """Clean up LightRAG resources."""
        if self.rag:
            try:
                await self.rag.finalize_storages()
            except:
                pass
    
    def get_status(self) -> Dict:
        """Get engine status."""
        return {
            "initialized": self.is_initialized,
            "has_lightrag": HAS_LIGHTRAG,
            "working_dir": self.working_dir,
            "documents_count": len(self.documents),
            "indexed": Path(self.working_dir, ".indexed").exists()
        }


# Singleton instance
_engine_instance: Optional[LightRAGEngine] = None


def get_lightrag_engine() -> LightRAGEngine:
    """Get singleton LightRAG engine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = LightRAGEngine()
    return _engine_instance


async def init_engine():
    """Initialize the LightRAG engine (call at startup)."""
    engine = get_lightrag_engine()
    await engine.initialize()
    return engine


# For testing
if __name__ == "__main__":
    async def test():
        engine = LightRAGEngine()
        print("Status:", engine.get_status())
        
        if HAS_LIGHTRAG:
            await engine.initialize()
            print("After init:", engine.get_status())
            
            # Index documents
            await engine.index_documents()
            
            # Test query
            result = await engine.query("What is medical negligence?")
            print("Query result:", result.get("answer", "No answer")[:500])
            
            await engine.finalize()
    
    asyncio.run(test())
