"""
faiss_search.py - Keyword-based search engine for Legal Lens.

Pure keyword search with TF-IDF style scoring.
No ML dependencies required - works on any hosting!

To add new documents:
1. Add them to data/documents.json
2. Or use build_index.py for PDF processing (run locally)
"""

import json
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass


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
    Keyword-based search engine.
    
    Uses TF-IDF style matching - no ML dependencies!
    Works on memory-constrained hosting like Render free tier.
    """
    
    def __init__(self, data_dir: str = None):
        # Use absolute path based on this file's location
        if data_dir is None:
            self.data_dir = Path(__file__).parent.parent / "data"
        else:
            self.data_dir = Path(data_dir)
        
        self.documents = []
        
        # Load documents
        self._load_documents()
    
    def _load_documents(self):
        """Load documents from JSON file."""
        docs_file = self.data_dir / "documents.json"
        
        if docs_file.exists():
            try:
                with open(docs_file, "r", encoding="utf-8") as f:
                    self.documents = json.load(f)
                print(f"[Search] Loaded {len(self.documents)} documents")
            except Exception as e:
                print(f"[Search] Error loading documents: {e}")
                self._create_sample_documents()
        else:
            print(f"[Search] No documents file found, creating samples")
            self._create_sample_documents()
    
    def _create_sample_documents(self):
        """Create sample documents if none exist."""
        self.documents = [
            {
                "doc_id": "jacob_mathew_2005",
                "title": "Jacob Mathew vs State of Punjab (2005)",
                "content": "This landmark case established the comprehensive law on medical negligence in India. The Supreme Court held that a medical professional can only be held liable for negligence if it is established that he did not possess the requisite skill or did not exercise reasonable care. The court laid down specific guidelines for prosecuting medical professionals.",
                "keywords": ["medical negligence", "doctor liability", "malpractice", "prosecution", "supreme court"],
                "statutes": ["IPC 304A", "BNS 106"],
                "year": 2005,
                "court": "Supreme Court of India"
            },
            {
                "doc_id": "puttaswamy_2017",
                "title": "K.S. Puttaswamy vs Union of India (2017)",
                "content": "The landmark Right to Privacy judgment. A nine-judge Constitution Bench unanimously held that right to privacy is a fundamental right intrinsic to Article 21 (right to life and personal liberty). Privacy includes bodily autonomy, personal identity, informational privacy, and decisional privacy. This judgment is foundational for data protection law in India.",
                "keywords": ["privacy", "fundamental right", "article 21", "data protection", "aadhaar"],
                "statutes": ["Article 21", "Article 14", "Article 19"],
                "year": 2017,
                "court": "Supreme Court of India"
            },
            {
                "doc_id": "navtej_johar_2018",
                "title": "Navtej Singh Johar vs Union of India (2018)",
                "content": "The Supreme Court decriminalized homosexuality by reading down Section 377 of the Indian Penal Code. Consensual sexual conduct between adults of the same sex in private is not a crime. Section 377 is unconstitutional to the extent it criminalizes consensual homosexual acts. The right to sexual orientation and gender identity is protected under Article 21.",
                "keywords": ["section 377", "homosexuality", "LGBTQ", "decriminalization", "privacy", "dignity"],
                "statutes": ["IPC 377", "Article 14", "Article 21"],
                "year": 2018,
                "court": "Supreme Court of India"
            },
            {
                "doc_id": "kesavananda_bharati_1973",
                "title": "Kesavananda Bharati vs State of Kerala (1973)",
                "content": "The most important constitutional law case in India. The Supreme Court established the Basic Structure Doctrine. Parliament has the power to amend any part of the Constitution but cannot amend the basic structure. Basic structure includes fundamental rights, secularism, federalism, separation of powers, judicial review, and democracy.",
                "keywords": ["basic structure", "constitution", "amendment", "parliament power", "fundamental rights"],
                "statutes": ["Article 368", "Article 13"],
                "year": 1973,
                "court": "Supreme Court of India"
            },
            {
                "doc_id": "vishaka_1997",
                "title": "Vishaka vs State of Rajasthan (1997)",
                "content": "Landmark case that laid down guidelines for prevention of sexual harassment at workplace. Sexual harassment at workplace violates fundamental rights under Articles 14, 19(1)(g), and 21. The court laid down binding guidelines known as Vishaka Guidelines. These guidelines have the force of law until proper legislation is enacted.",
                "keywords": ["sexual harassment", "workplace", "vishaka guidelines", "women's rights", "POSH"],
                "statutes": ["Article 14", "Article 19", "Article 21", "POSH Act 2013"],
                "year": 1997,
                "court": "Supreme Court of India"
            }
        ]
        
        # Save for future use
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.data_dir / "documents.json", "w", encoding="utf-8") as f:
            json.dump(self.documents, f, indent=2, ensure_ascii=False)
    
    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """
        Search using TF-IDF style keyword matching.
        """
        query_lower = query.lower()
        query_words = [w.strip() for w in query_lower.split() if len(w.strip()) > 2]
        
        if not query_words:
            return []
        
        scored_docs = []
        
        for doc in self.documents:
            score = self._calculate_score(query_words, doc)
            
            if score > 0:
                scored_docs.append((doc, score))
        
        # Sort by score descending
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Build results
        results = []
        for doc, score in scored_docs[:top_k]:
            results.append(SearchResult(
                doc_id=doc["doc_id"],
                title=doc.get("title", ""),
                content=doc.get("content", "")[:500],
                score=min(score, 1.0),
                source="keyword",
                metadata={
                    "year": doc.get("year"),
                    "court": doc.get("court"),
                    "statutes": doc.get("statutes", []),
                    "keywords": doc.get("keywords", [])
                }
            ))
        
        return results
    
    def _calculate_score(self, query_words: List[str], doc: Dict) -> float:
        """Calculate relevance score using TF-IDF style matching."""
        score = 0.0
        
        title = doc.get("title", "").lower()
        content = doc.get("content", "").lower()
        keywords = [k.lower() for k in doc.get("keywords", [])]
        statutes = " ".join(doc.get("statutes", [])).lower()
        
        for word in query_words:
            # Title match (highest weight)
            if word in title:
                score += 0.35
            
            # Keyword match (high weight)
            for kw in keywords:
                if word in kw or kw in word:
                    score += 0.30
                    break
            
            # Statute reference match
            if word in statutes:
                score += 0.25
            
            # Content match (lower weight, capped)
            word_count = content.count(word)
            if word_count > 0:
                score += min(word_count * 0.03, 0.15)
        
        return score
    
    def get_document_count(self) -> int:
        """Get number of indexed documents."""
        return len(self.documents)


# Singleton instance
_search_engine = None

def get_search_engine(data_dir: str = None) -> FAISSSearchEngine:
    """Get or create the search engine instance."""
    global _search_engine
    if _search_engine is None:
        _search_engine = FAISSSearchEngine(data_dir)
    return _search_engine
