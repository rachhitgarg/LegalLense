"""
embeddings.py - Embedding generation module using BGE-M3.

BGE-M3 Rationale:
-----------------
1. **Multilingual**: Supports English, Hindi, and 100+ languages - essential for
   Indian legal documents that mix English and Hindi.
2. **High Quality**: State-of-the-art performance on retrieval benchmarks.
3. **Efficient**: Can run on CPU with 16GB RAM using the base model.
4. **Dense + Sparse**: Supports both dense and sparse embeddings for hybrid search.
"""

import os
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Use sentence-transformers for easy BGE-M3 loading
# Alternative: from FlagEmbedding import BGEM3FlagModel
from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """Service for generating embeddings and storing in Qdrant."""
    
    COLLECTION_NAME = "legal_documents"
    EMBEDDING_DIM = 1024  # BGE-M3 dimension
    
    def __init__(
        self,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        model_name: str = "BAAI/bge-m3",
        use_memory: bool = False,  # Use in-memory mode if True
        persist_path: str = None,  # Path to persist data locally
        cloud_url: str = None,     # Qdrant Cloud URL
        api_key: str = None,       # Qdrant Cloud API key
    ):
        # Initialize Qdrant client
        if cloud_url and api_key:
            # Qdrant Cloud mode
            self.qdrant = QdrantClient(url=cloud_url, api_key=api_key)
            print(f"[Qdrant] Connected to Qdrant Cloud")
        elif use_memory:
            # In-memory mode - no server needed, data lost on restart
            self.qdrant = QdrantClient(":memory:")
            print("[Qdrant] Running in MEMORY mode (no persistence)")
        elif persist_path:
            # Local persistence mode - no server needed, data saved to disk
            self.qdrant = QdrantClient(path=persist_path)
            print(f"[Qdrant] Running in LOCAL mode (data saved to {persist_path})")
        else:
            # Server mode - requires Qdrant server running
            try:
                self.qdrant = QdrantClient(host=qdrant_host, port=qdrant_port)
                self.qdrant.get_collections()  # Test connection
                print(f"[Qdrant] Connected to server at {qdrant_host}:{qdrant_port}")
            except Exception as e:
                print(f"[Qdrant] Server not available, falling back to local mode")
                persist_path = "./qdrant_data"
                self.qdrant = QdrantClient(path=persist_path)
                print(f"[Qdrant] Running in LOCAL mode (data saved to {persist_path})")
        
        # Load embedding model
        print(f"[Embeddings] Loading model {model_name}...")
        self.model = SentenceTransformer(model_name)
        print(f"[Embeddings] Model loaded successfully")
        
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Create the collection if it doesn't exist."""
        collections = [c.name for c in self.qdrant.get_collections().collections]
        if self.COLLECTION_NAME not in collections:
            self.qdrant.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=self.EMBEDDING_DIM,
                    distance=Distance.COSINE,
                ),
            )
            print(f"[Qdrant] Created collection '{self.COLLECTION_NAME}'")
    
    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        return self.model.encode(text, normalize_embeddings=True).tolist()
    
    def embed_documents(self, documents: list[dict]) -> None:
        """Embed and upsert documents into Qdrant."""
        points = []
        for i, doc in enumerate(documents):
            embedding = self.embed_text(doc["content"])
            point = PointStruct(
                id=i,
                vector=embedding,
                payload={
                    "doc_id": doc["id"],
                    "filename": doc["filename"],
                    "source_type": doc["source_type"],
                    "content_preview": doc["content"][:500],
                },
            )
            points.append(point)
        
        self.qdrant.upsert(collection_name=self.COLLECTION_NAME, points=points)
    
    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """Search for similar documents."""
        query_vector = self.embed_text(query)
        # Use query method (new API) instead of search (deprecated)
        results = self.qdrant.query_points(
            collection_name=self.COLLECTION_NAME,
            query=query_vector,
            limit=top_k,
        )
        return [
            {
                "id": hit.id,
                "score": hit.score,
                "payload": hit.payload,
            }
            for hit in results.points
        ]


if __name__ == "__main__":
    # Quick test
    service = EmbeddingService()
    print("Embedding service initialized successfully.")
