"""
local_search.py - Self-contained search engine for Legal Lens.

No external databases required! Uses:
- JSON files for document storage
- TF-IDF for text search
- NetworkX for knowledge graph

This makes the app truly portable and deployable anywhere.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import re


@dataclass
class SearchResult:
    doc_id: str
    content: str
    score: float
    source: str
    metadata: Dict = None


class LocalSearchEngine:
    """
    Local search engine using TF-IDF and keyword matching.
    
    No external vector database required!
    """
    
    def __init__(self, data_dir: str = "../data"):
        self.data_dir = Path(data_dir)
        self.documents = []
        self.doc_index_file = self.data_dir / "document_index.json"
        
        # Load documents
        self._load_documents()
    
    def _load_documents(self):
        """Load documents from JSON index."""
        if self.doc_index_file.exists():
            with open(self.doc_index_file, "r", encoding="utf-8") as f:
                self.documents = json.load(f)
        else:
            # Create from sample data
            self._create_sample_documents()
    
    def _create_sample_documents(self):
        """Create sample documents for demo."""
        self.documents = [
            {
                "doc_id": "jacob_mathew_2005",
                "title": "Jacob Mathew vs State of Punjab (2005)",
                "content": "This landmark case established the law on medical negligence in India. The Supreme Court held that a medical professional can only be held liable for negligence if it is established that he did not possess the requisite skill which he professed to have, or he did not exercise reasonable care in its exercise. The court laid down specific guidelines for prosecuting medical professionals.",
                "keywords": ["medical negligence", "doctor", "prosecution", "supreme court", "jacob mathew"],
                "statutes": ["IPC 304A", "BNS 106"],
                "year": 2005
            },
            {
                "doc_id": "kesavananda_bharati_1973",
                "title": "Kesavananda Bharati vs State of Kerala (1973)",
                "content": "This is the most important constitutional law case in India. The Supreme Court established the Basic Structure Doctrine, holding that Parliament cannot amend the Constitution to destroy its basic structure. This includes fundamental rights, secularism, federalism, and judicial review. The 13-judge bench decision is a cornerstone of Indian constitutional law.",
                "keywords": ["basic structure", "constitution", "amendment", "parliament", "fundamental rights"],
                "statutes": ["Article 368", "Article 13"],
                "year": 1973
            },
            {
                "doc_id": "navtej_johar_2018",
                "title": "Navtej Singh Johar vs Union of India (2018)",
                "content": "The Supreme Court decriminalized homosexuality by reading down Section 377 of IPC. The court held that consensual sexual conduct between adults of the same sex in private is not a crime. This historic judgment upheld the right to equality, privacy, and dignity of LGBTQ+ individuals. Section 377 was declared unconstitutional to the extent it criminalized consensual homosexual acts.",
                "keywords": ["section 377", "homosexuality", "LGBTQ", "decriminalization", "privacy", "dignity"],
                "statutes": ["IPC 377"],
                "year": 2018
            },
            {
                "doc_id": "puttaswamy_2017",
                "title": "K.S. Puttaswamy vs Union of India (2017)",
                "content": "The Right to Privacy case. A nine-judge Constitution Bench unanimously held that right to privacy is a fundamental right protected under Article 21 of the Constitution. The court held that privacy is intrinsic to life, liberty, and freedom. This judgment has implications for data protection, surveillance, and personal autonomy.",
                "keywords": ["privacy", "fundamental right", "article 21", "aadhaar", "data protection"],
                "statutes": ["Article 21", "Article 14", "Article 19"],
                "year": 2017
            },
            {
                "doc_id": "vineeta_sharma_2020",
                "title": "Vineeta Sharma vs Rakesh Sharma (2020)",
                "content": "This case clarified the Hindu Succession (Amendment) Act, 2005. The Supreme Court held that daughters have equal coparcenary rights by birth, irrespective of whether the father was alive on the date of amendment. This ensures gender equality in inheritance of ancestral property.",
                "keywords": ["hindu succession", "coparcenary", "daughter", "inheritance", "property rights"],
                "statutes": ["Hindu Succession Act"],
                "year": 2020
            }
        ]
        
        # Save to file
        self._save_documents()
    
    def _save_documents(self):
        """Save documents to JSON file."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.doc_index_file, "w", encoding="utf-8") as f:
            json.dump(self.documents, f, indent=2, ensure_ascii=False)
    
    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """
        Search documents using keyword matching and TF-IDF-like scoring.
        """
        query_terms = self._tokenize(query.lower())
        results = []
        
        for doc in self.documents:
            # Calculate relevance score
            score = self._calculate_score(query_terms, doc)
            
            if score > 0:
                results.append(SearchResult(
                    doc_id=doc["doc_id"],
                    content=doc["content"][:500],
                    score=score,
                    source="local",
                    metadata={
                        "title": doc.get("title", ""),
                        "year": doc.get("year"),
                        "statutes": doc.get("statutes", [])
                    }
                ))
        
        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        # Remove punctuation and split
        text = re.sub(r'[^\w\s]', ' ', text)
        return [w for w in text.split() if len(w) > 2]
    
    def _calculate_score(self, query_terms: List[str], doc: Dict) -> float:
        """Calculate relevance score for a document."""
        score = 0.0
        
        # Search in title (highest weight)
        title = doc.get("title", "").lower()
        for term in query_terms:
            if term in title:
                score += 3.0
        
        # Search in keywords (high weight)
        keywords = [k.lower() for k in doc.get("keywords", [])]
        for term in query_terms:
            for kw in keywords:
                if term in kw or kw in term:
                    score += 2.0
        
        # Search in content (medium weight)
        content = doc.get("content", "").lower()
        for term in query_terms:
            count = content.count(term)
            score += count * 0.5
        
        # Search in statutes
        statutes = [s.lower() for s in doc.get("statutes", [])]
        for term in query_terms:
            for statute in statutes:
                if term in statute:
                    score += 2.5
        
        # Normalize
        if score > 0:
            score = min(score / 10.0, 1.0)  # Cap at 1.0
        
        return score
    
    def add_document(self, doc_id: str, title: str, content: str, 
                    keywords: List[str] = None, statutes: List[str] = None, year: int = None):
        """Add a new document to the index."""
        self.documents.append({
            "doc_id": doc_id,
            "title": title,
            "content": content,
            "keywords": keywords or [],
            "statutes": statutes or [],
            "year": year
        })
        self._save_documents()
    
    def get_document_count(self) -> int:
        """Get number of indexed documents."""
        return len(self.documents)


# Singleton instance
_search_engine = None

def get_search_engine(data_dir: str = "../data") -> LocalSearchEngine:
    """Get or create the search engine instance."""
    global _search_engine
    if _search_engine is None:
        _search_engine = LocalSearchEngine(data_dir)
    return _search_engine
