"""
semantic_search.py - Semantic Search with OpenAI Embeddings + FAISS + KG + RAG

This provides a complete semantic search solution:
1. OpenAI Embeddings API - for query vectorization (lightweight, API-based)
2. FAISS - for similarity search with pre-computed document embeddings
3. NetworkX KG - for statute mappings and relationships
4. Groq LLM - for RAG-style answer generation

No heavy ML dependencies on server! Just API calls.
"""

import json
import os
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import httpx


@dataclass
class SearchResult:
    doc_id: str
    title: str
    content: str
    score: float
    source: str
    metadata: Dict = None


class SemanticSearchEngine:
    """
    Semantic Search Engine using OpenAI Embeddings.
    
    Features:
    - Semantic search using embeddings (not just keywords)
    - Pre-computed document embeddings (generated locally)
    - OpenAI API for query encoding (lightweight on server)
    - FAISS/numpy for similarity search
    - KG integration for statute mappings
    """
    
    EMBEDDING_DIM = 1536  # OpenAI text-embedding-3-small dimension
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            self.data_dir = Path(__file__).parent.parent / "data"
        else:
            self.data_dir = Path(data_dir)
        
        self.documents = []
        self.embeddings = None
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        
        # Load pre-computed data
        self._load_data()
    
    def _load_data(self):
        """Load documents and pre-computed embeddings."""
        docs_file = self.data_dir / "documents.json"
        embeddings_file = self.data_dir / "openai_embeddings.npy"
        
        # Load documents
        if docs_file.exists():
            with open(docs_file, "r", encoding="utf-8") as f:
                self.documents = json.load(f)
            print(f"[Semantic] Loaded {len(self.documents)} documents")
        else:
            self._create_sample_documents()
        
        # Load pre-computed embeddings
        if embeddings_file.exists():
            self.embeddings = np.load(embeddings_file)
            print(f"[Semantic] Loaded embeddings: {self.embeddings.shape}")
        else:
            print("[Semantic] No pre-computed embeddings found. Run build_openai_index.py locally.")
            # Will fall back to keyword search
    
    def _create_sample_documents(self):
        """Create sample documents."""
        self.documents = [
            {
                "doc_id": "jacob_mathew_2005",
                "title": "Jacob Mathew vs State of Punjab (2005)",
                "content": "This landmark case established the comprehensive law on medical negligence in India. The Supreme Court held that a medical professional can only be held liable for negligence if it is established that he did not possess the requisite skill or did not exercise reasonable care. The court laid down specific guidelines for prosecuting medical professionals including that private complaints cannot be entertained unless a prima facie case of negligence exists.",
                "keywords": ["medical negligence", "doctor liability", "malpractice", "prosecution"],
                "statutes": ["IPC 304A", "BNS 106"],
                "year": 2005,
                "court": "Supreme Court of India"
            },
            {
                "doc_id": "puttaswamy_2017",
                "title": "K.S. Puttaswamy vs Union of India (2017)",
                "content": "The landmark Right to Privacy judgment. A nine-judge Constitution Bench unanimously held that right to privacy is a fundamental right intrinsic to Article 21. Privacy includes bodily autonomy, personal identity, informational privacy, and decisional privacy. This judgment is foundational for data protection law in India and overruled previous contrary judgments.",
                "keywords": ["privacy", "fundamental right", "article 21", "data protection"],
                "statutes": ["Article 21", "Article 14", "Article 19"],
                "year": 2017,
                "court": "Supreme Court of India"
            },
            {
                "doc_id": "navtej_johar_2018",
                "title": "Navtej Singh Johar vs Union of India (2018)",
                "content": "The Supreme Court decriminalized homosexuality by reading down Section 377 of the Indian Penal Code. Consensual sexual conduct between adults of the same sex in private is not a crime. Section 377 is unconstitutional to the extent it criminalizes consensual homosexual acts between adults. The court emphasized constitutional morality over social morality.",
                "keywords": ["section 377", "homosexuality", "LGBTQ", "decriminalization"],
                "statutes": ["IPC 377", "Article 14", "Article 21"],
                "year": 2018,
                "court": "Supreme Court of India"
            },
            {
                "doc_id": "kesavananda_bharati_1973",
                "title": "Kesavananda Bharati vs State of Kerala (1973)",
                "content": "The most important constitutional law case in India establishing the Basic Structure Doctrine. The Supreme Court held that Parliament has the power to amend any part of the Constitution but cannot amend the basic structure. Basic structure includes fundamental rights, secularism, federalism, separation of powers, judicial review, and democracy.",
                "keywords": ["basic structure", "constitution", "amendment", "fundamental rights"],
                "statutes": ["Article 368", "Article 13"],
                "year": 1973,
                "court": "Supreme Court of India"
            },
            {
                "doc_id": "vishaka_1997",
                "title": "Vishaka vs State of Rajasthan (1997)",
                "content": "Landmark case that laid down guidelines for prevention of sexual harassment at workplace known as Vishaka Guidelines. Sexual harassment at workplace violates fundamental rights under Articles 14, 19(1)(g), and 21. The court filled the legislative vacuum by laying down binding guidelines which were later codified as the POSH Act 2013.",
                "keywords": ["sexual harassment", "workplace", "vishaka guidelines", "women rights"],
                "statutes": ["Article 14", "Article 19", "Article 21", "POSH Act"],
                "year": 1997,
                "court": "Supreme Court of India"
            }
        ]
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.data_dir / "documents.json", "w", encoding="utf-8") as f:
            json.dump(self.documents, f, indent=2, ensure_ascii=False)
    
    async def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get embedding for text using OpenAI API."""
        if not self.openai_key:
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.openai_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "text-embedding-3-small",
                        "input": text
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    embedding = np.array(data["data"][0]["embedding"])
                    return embedding
                else:
                    print(f"[Semantic] OpenAI API error: {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"[Semantic] Embedding error: {e}")
            return None
    
    async def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """
        Semantic search using OpenAI embeddings.
        Falls back to keyword search if embeddings unavailable.
        """
        # Try semantic search first
        if self.embeddings is not None and self.openai_key:
            query_embedding = await self.get_embedding(query)
            
            if query_embedding is not None:
                return self._vector_search(query_embedding, top_k)
        
        # Fallback to keyword search
        return self._keyword_search(query, top_k)
    
    def _vector_search(self, query_embedding: np.ndarray, top_k: int) -> List[SearchResult]:
        """Search using cosine similarity with pre-computed embeddings."""
        # Normalize
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        doc_norms = self.embeddings / np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        
        # Compute similarities
        similarities = np.dot(doc_norms, query_norm)
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if idx < len(self.documents):
                doc = self.documents[idx]
                results.append(SearchResult(
                    doc_id=doc["doc_id"],
                    title=doc.get("title", ""),
                    content=doc.get("content", "")[:500],
                    score=float(similarities[idx]),
                    source="semantic",
                    metadata={
                        "year": doc.get("year"),
                        "court": doc.get("court"),
                        "statutes": doc.get("statutes", []),
                        "keywords": doc.get("keywords", [])
                    }
                ))
        
        return results
    
    def _keyword_search(self, query: str, top_k: int) -> List[SearchResult]:
        """Fallback keyword search."""
        query_lower = query.lower()
        query_words = [w for w in query_lower.split() if len(w) > 2]
        
        scored = []
        for doc in self.documents:
            score = 0.0
            title = doc.get("title", "").lower()
            content = doc.get("content", "").lower()
            keywords = [k.lower() for k in doc.get("keywords", [])]
            
            for word in query_words:
                if word in title:
                    score += 0.35
                for kw in keywords:
                    if word in kw:
                        score += 0.30
                score += min(content.count(word) * 0.03, 0.15)
            
            if score > 0:
                scored.append((doc, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for doc, score in scored[:top_k]:
            results.append(SearchResult(
                doc_id=doc["doc_id"],
                title=doc.get("title", ""),
                content=doc.get("content", "")[:500],
                score=min(score, 1.0),
                source="keyword",
                metadata={
                    "year": doc.get("year"),
                    "statutes": doc.get("statutes", [])
                }
            ))
        
        return results
    
    def get_document_count(self) -> int:
        return len(self.documents)


# Singleton instance
_engine = None

def get_search_engine(data_dir: str = None) -> SemanticSearchEngine:
    global _engine
    if _engine is None:
        _engine = SemanticSearchEngine(data_dir)
    return _engine
