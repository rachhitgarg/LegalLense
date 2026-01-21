"""
faiss_search.py - FAISS-based semantic search engine for Legal Lens.

Uses:
- FAISS for fast vector similarity search (runs locally)
- sentence-transformers for embeddings
- JSON for document storage

This provides semantic search quality similar to Qdrant, but fully local!
"""

import json
import os
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import pickle


@dataclass
class SearchResult:
    doc_id: str
    title: str
    content: str
    score: float
    source: str
    metadata: Dict = None


class FAISSSearchEngine:
    """
    FAISS-based semantic search engine.
    
    Uses sentence-transformers for embeddings and FAISS for similarity search.
    No external services required!
    """
    
    def __init__(self, data_dir: str = "../data", model_name: str = "all-MiniLM-L6-v2"):
        self.data_dir = Path(data_dir)
        self.model_name = model_name
        self.documents = []
        self.index = None
        self.model = None
        
        # File paths
        self.docs_file = self.data_dir / "documents.json"
        self.index_file = self.data_dir / "faiss_index.pkl"
        
        # Initialize
        self._load_model()
        self._load_or_create_index()
    
    def _load_model(self):
        """Load the embedding model."""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            print(f"[FAISS] Loaded embedding model: {self.model_name}")
        except Exception as e:
            print(f"[FAISS] Error loading model: {e}")
            self.model = None
    
    def _load_or_create_index(self):
        """Load existing index or create new one."""
        if self.docs_file.exists() and self.index_file.exists():
            self._load_index()
        else:
            self._create_default_documents()
            self._build_index()
    
    def _create_default_documents(self):
        """Create default legal documents for demo."""
        self.documents = [
            {
                "doc_id": "jacob_mathew_2005",
                "title": "Jacob Mathew vs State of Punjab (2005)",
                "content": """This landmark case established the comprehensive law on medical negligence in India. 
The Supreme Court held that a medical professional can only be held liable for negligence if it is established that:
1. He did not possess the requisite skill which he professed to have
2. He did not exercise reasonable care in its exercise

The court laid down specific guidelines for prosecuting medical professionals, including:
- Private complaints cannot be entertained unless a prima facie case of negligence exists
- Simple lack of care, error of judgment, or accident is not negligence
- The doctor must be shown to have acted with gross negligence or recklessness

This case is fundamental for understanding medical malpractice law in India.""",
                "keywords": ["medical negligence", "doctor liability", "malpractice", "prosecution", "supreme court"],
                "statutes": ["IPC 304A", "BNS 106"],
                "year": 2005,
                "court": "Supreme Court of India"
            },
            {
                "doc_id": "kesavananda_bharati_1973",
                "title": "Kesavananda Bharati vs State of Kerala (1973)",
                "content": """The most important constitutional law case in India. The Supreme Court established the Basic Structure Doctrine.

Key holdings:
1. Parliament has the power to amend any part of the Constitution
2. However, Parliament cannot amend the basic structure or framework of the Constitution
3. Basic structure includes: fundamental rights, secularism, federalism, separation of powers, judicial review, democracy

The 13-judge bench decision (7-6 majority) is a cornerstone of Indian constitutional jurisprudence. It limits parliamentary power and protects essential constitutional values.

This doctrine has been applied to strike down several constitutional amendments that attempted to curtail judicial review or fundamental rights.""",
                "keywords": ["basic structure", "constitution", "amendment", "parliament power", "fundamental rights", "constitutional law"],
                "statutes": ["Article 368", "Article 13"],
                "year": 1973,
                "court": "Supreme Court of India"
            },
            {
                "doc_id": "navtej_johar_2018",
                "title": "Navtej Singh Johar vs Union of India (2018)",
                "content": """The Supreme Court decriminalized homosexuality by reading down Section 377 of the Indian Penal Code.

Key holdings:
1. Consensual sexual conduct between adults of the same sex in private is not a crime
2. Section 377 is unconstitutional to the extent it criminalizes consensual homosexual acts
3. The right to sexual orientation and gender identity is protected under Article 21 (right to life and dignity)
4. LGBTQ+ individuals have equal rights to privacy and dignity

This historic judgment overruled Suresh Kumar Koushal (2013) and upheld:
- Right to equality (Article 14)
- Freedom of expression (Article 19)
- Right to privacy and dignity (Article 21)

The court emphasized that constitutional morality must prevail over social morality.""",
                "keywords": ["section 377", "homosexuality", "LGBTQ", "decriminalization", "privacy", "dignity", "equality"],
                "statutes": ["IPC 377", "Article 14", "Article 21"],
                "year": 2018,
                "court": "Supreme Court of India"
            },
            {
                "doc_id": "puttaswamy_2017",
                "title": "K.S. Puttaswamy vs Union of India (2017)",
                "content": """The landmark Right to Privacy judgment. A nine-judge Constitution Bench unanimously held that right to privacy is a fundamental right.

Key holdings:
1. Right to privacy is intrinsic to Article 21 (right to life and personal liberty)
2. Privacy includes: bodily autonomy, personal identity, informational privacy, decisional privacy
3. Privacy is not absolute and can be restricted under a three-fold test:
   - Legitimate state aim
   - Law that is fair, just, and reasonable
   - Proportionality

Implications:
- Right to control personal data
- Protection against surveillance
- Sexual orientation is a matter of privacy
- Overruled MP Sharma (1954) and Kharak Singh (1962)

This judgment is foundational for data protection law in India.""",
                "keywords": ["privacy", "fundamental right", "article 21", "aadhaar", "data protection", "surveillance", "autonomy"],
                "statutes": ["Article 21", "Article 14", "Article 19"],
                "year": 2017,
                "court": "Supreme Court of India"
            },
            {
                "doc_id": "vineeta_sharma_2020",
                "title": "Vineeta Sharma vs Rakesh Sharma (2020)",
                "content": """This case clarified the Hindu Succession (Amendment) Act, 2005 regarding daughters' coparcenary rights.

Key holdings:
1. Daughters have equal coparcenary rights by birth
2. This right exists irrespective of whether the father was alive on the date of the 2005 amendment
3. The right is by birth, not by the date of the amendment coming into force
4. Daughters have the same rights as sons in ancestral property

This ensures gender equality in inheritance of Hindu Undivided Family (HUF) ancestral property.

The court overruled the contrary view in Prakash vs Phulavati (2015) and Danamma vs Amar (2018).""",
                "keywords": ["hindu succession", "coparcenary", "daughter rights", "inheritance", "property", "gender equality", "ancestral property"],
                "statutes": ["Hindu Succession Act 1956", "Hindu Succession Amendment Act 2005"],
                "year": 2020,
                "court": "Supreme Court of India"
            },
            {
                "doc_id": "maneka_gandhi_1978",
                "title": "Maneka Gandhi vs Union of India (1978)",
                "content": """This case expanded the scope of Article 21 (right to life and personal liberty).

Key holdings:
1. Right to live is not merely physical existence but the right to live with human dignity
2. Procedure established by law must be fair, just, and reasonable
3. Articles 14, 19, and 21 are interconnected - any law affecting personal liberty must satisfy all three
4. 'Procedure established by law' was harmonized with 'due process of law'

This case revolutionized constitutional interpretation in India by:
- Expanding fundamental rights beyond literal interpretation
- Establishing that arbitrariness violates Article 14
- Creating the foundation for public interest litigation

Many subsequent rights (education, health, livelihood, shelter) were derived from this expansive reading of Article 21.""",
                "keywords": ["article 21", "right to life", "personal liberty", "due process", "fundamental rights", "dignity", "fair procedure"],
                "statutes": ["Article 21", "Article 14", "Article 19"],
                "year": 1978,
                "court": "Supreme Court of India"
            },
            {
                "doc_id": "vishaka_1997",
                "title": "Vishaka vs State of Rajasthan (1997)",
                "content": """Landmark case that laid down guidelines for prevention of sexual harassment at workplace.

Key holdings:
1. Sexual harassment at workplace violates fundamental rights under Articles 14, 19(1)(g), and 21
2. In absence of legislation, the court laid down binding guidelines known as 'Vishaka Guidelines'
3. These guidelines have the force of law until proper legislation is enacted
4. Employers must establish complaint committees and follow prescribed procedures

The guidelines were later codified as the Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013.

This case is significant for:
- Judicial activism in protecting women's rights
- Recognition of international conventions (CEDAW) in Indian law
- Filling legislative vacuum through guidelines""",
                "keywords": ["sexual harassment", "workplace", "vishaka guidelines", "women's rights", "gender discrimination", "POSH Act"],
                "statutes": ["Article 14", "Article 19", "Article 21", "POSH Act 2013"],
                "year": 1997,
                "court": "Supreme Court of India"
            }
        ]
        
        # Save documents
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.docs_file, "w", encoding="utf-8") as f:
            json.dump(self.documents, f, indent=2, ensure_ascii=False)
    
    def _build_index(self):
        """Build FAISS index from documents."""
        if not self.model or not self.documents:
            return
        
        try:
            import faiss
            
            # Create embeddings for all documents
            texts = [f"{doc['title']} {doc['content']}" for doc in self.documents]
            embeddings = self.model.encode(texts, show_progress_bar=False)
            
            # Create FAISS index
            dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatIP(dimension)  # Inner product (cosine similarity with normalized vectors)
            
            # Normalize and add
            faiss.normalize_L2(embeddings)
            self.index.add(embeddings)
            
            # Save index
            self._save_index()
            print(f"[FAISS] Built index with {len(self.documents)} documents")
            
        except ImportError:
            print("[FAISS] faiss-cpu not installed, falling back to numpy search")
            self._build_numpy_index()
    
    def _build_numpy_index(self):
        """Fallback: Build index using numpy (slower but no FAISS dependency)."""
        if not self.model or not self.documents:
            return
        
        texts = [f"{doc['title']} {doc['content']}" for doc in self.documents]
        embeddings = self.model.encode(texts, show_progress_bar=False)
        
        # Normalize
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        self.embeddings = embeddings / norms
        
        self._save_index()
        print(f"[FAISS] Built numpy index with {len(self.documents)} documents")
    
    def _save_index(self):
        """Save index and documents."""
        data = {
            "documents": self.documents,
            "embeddings": getattr(self, "embeddings", None)
        }
        
        # If using FAISS, save the index separately
        if self.index is not None:
            try:
                import faiss
                faiss.write_index(self.index, str(self.data_dir / "faiss.index"))
            except:
                pass
        
        with open(self.index_file, "wb") as f:
            pickle.dump(data, f)
    
    def _load_index(self):
        """Load existing index."""
        with open(self.docs_file, "r", encoding="utf-8") as f:
            self.documents = json.load(f)
        
        with open(self.index_file, "rb") as f:
            data = pickle.load(f)
            self.embeddings = data.get("embeddings")
        
        # Try to load FAISS index
        faiss_path = self.data_dir / "faiss.index"
        if faiss_path.exists():
            try:
                import faiss
                self.index = faiss.read_index(str(faiss_path))
                print(f"[FAISS] Loaded FAISS index with {self.index.ntotal} vectors")
            except:
                print("[FAISS] Using numpy fallback")
    
    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """
        Semantic search using embeddings.
        """
        if not self.model:
            return self._fallback_keyword_search(query, top_k)
        
        # Encode query
        query_embedding = self.model.encode([query], show_progress_bar=False)
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        
        # Search using FAISS or numpy
        if self.index is not None:
            try:
                import faiss
                faiss.normalize_L2(query_embedding)
                scores, indices = self.index.search(query_embedding, min(top_k, len(self.documents)))
                scores = scores[0]
                indices = indices[0]
            except:
                scores, indices = self._numpy_search(query_embedding, top_k)
        elif hasattr(self, "embeddings") and self.embeddings is not None:
            scores, indices = self._numpy_search(query_embedding, top_k)
        else:
            return self._fallback_keyword_search(query, top_k)
        
        # Build results
        results = []
        for i, (score, idx) in enumerate(zip(scores, indices)):
            if idx < 0 or idx >= len(self.documents):
                continue
            doc = self.documents[idx]
            results.append(SearchResult(
                doc_id=doc["doc_id"],
                title=doc.get("title", ""),
                content=doc["content"][:500],
                score=float(score),
                source="faiss",
                metadata={
                    "year": doc.get("year"),
                    "court": doc.get("court"),
                    "statutes": doc.get("statutes", [])
                }
            ))
        
        return results
    
    def _numpy_search(self, query_embedding: np.ndarray, top_k: int):
        """Fallback search using numpy."""
        scores = np.dot(self.embeddings, query_embedding.T).flatten()
        indices = np.argsort(scores)[::-1][:top_k]
        return scores[indices], indices
    
    def _fallback_keyword_search(self, query: str, top_k: int) -> List[SearchResult]:
        """Fallback to keyword search if embeddings fail."""
        query_lower = query.lower()
        results = []
        
        for doc in self.documents:
            score = 0
            content = doc.get("content", "").lower()
            title = doc.get("title", "").lower()
            
            for word in query_lower.split():
                if len(word) > 2:
                    score += content.count(word) * 0.5
                    score += title.count(word) * 2.0
            
            if score > 0:
                results.append(SearchResult(
                    doc_id=doc["doc_id"],
                    title=doc.get("title", ""),
                    content=doc["content"][:500],
                    score=min(score / 10, 1.0),
                    source="keyword",
                    metadata={"year": doc.get("year")}
                ))
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def get_document_count(self) -> int:
        """Get number of indexed documents."""
        return len(self.documents)
    
    def add_document(self, doc_id: str, title: str, content: str, **kwargs):
        """Add a new document and rebuild index."""
        self.documents.append({
            "doc_id": doc_id,
            "title": title,
            "content": content,
            **kwargs
        })
        self._build_index()


# Singleton instance
_search_engine = None

def get_search_engine(data_dir: str = "../data") -> FAISSSearchEngine:
    """Get or create the FAISS search engine instance."""
    global _search_engine
    if _search_engine is None:
        _search_engine = FAISSSearchEngine(data_dir)
    return _search_engine
