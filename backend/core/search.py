"""
Search Module for Legal Lens

Combines:
- Knowledge Graph traversal
- Keyword search over documents
- Score-based ranking
"""

import json
import os
import re
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from .knowledge_graph import get_knowledge_graph, KnowledgeGraph


class SearchEngine:
    """
    Search engine that combines KG and document search.
    """
    
    def __init__(self, documents_path: Optional[str] = None):
        """
        Initialize search engine.
        
        Args:
            documents_path: Path to documents.json
        """
        base_dir = Path(__file__).parent.parent
        self.documents_path = documents_path or str(base_dir / "data" / "documents.json")
        
        self.documents: List[Dict] = []
        self.kg: KnowledgeGraph = get_knowledge_graph()
        
        self._load_documents()
    
    def _load_documents(self):
        """Load judgment documents."""
        if not os.path.exists(self.documents_path):
            print(f"Warning: Documents not found at {self.documents_path}")
            return
        
        with open(self.documents_path, 'r', encoding='utf-8') as f:
            self.documents = json.load(f)
        
        print(f"Loaded {len(self.documents)} documents")
    
    def search(self, query: str, top_k: int = 5) -> Dict:
        """
        Perform hybrid search: KG + documents.
        
        Args:
            query: User query
            top_k: Number of results to return
        
        Returns:
            Search results with documents, KG info, and metadata
        """
        # 1. Extract statute references from query
        statute_info = self._extract_statute_info(query)
        
        # 2. Search KG for related nodes
        kg_results = self._search_kg(query, statute_info)
        
        # 3. Search documents with KG boosting
        doc_results = self._search_documents(query, kg_results, top_k)
        
        return {
            "query": query,
            "statute_mapping": statute_info.get("mapping"),
            "related_statutes": statute_info.get("related", []),
            "kg_concepts": kg_results.get("concepts", []),
            "results": doc_results,
            "total_results": len(doc_results)
        }
    
    def _extract_statute_info(self, query: str) -> Dict:
        """Extract and resolve statute references from query."""
        result = {"mapping": None, "related": []}
        
        # Pattern: IPC 302, Section 377, etc.
        patterns = [
            r'(?:IPC|ipc)\s*(?:section)?\s*(\d+[A-Za-z]?)',
            r'(?:section|Section)\s*(\d+[A-Za-z]?)\s*(?:of\s*)?(?:IPC|ipc)?',
            r'(?:CrPC|crpc)\s*(?:section)?\s*(\d+[A-Za-z]?)',
            r'(\d+[A-Za-z]?)\s*(?:IPC|ipc)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                section = match.group(1)
                
                # Determine code (default to IPC)
                code = "IPC"
                if "crpc" in query.lower():
                    code = "CrPC"
                
                # Get mapping
                mapping = self.kg.get_statute_mapping(code, section)
                if mapping:
                    result["mapping"] = mapping
                
                # Find judgments citing this statute
                citing_judgments = self.kg.find_judgments_citing_statute(code, section)
                result["related"] = [
                    {"id": j["id"], "title": j.get("title", "")}
                    for j in citing_judgments
                ]
                
                break
        
        return result
    
    def _search_kg(self, query: str, statute_info: Dict) -> Dict:
        """Search KG for relevant nodes."""
        concepts = []
        
        # Search for concepts in KG
        concept_results = self.kg.search_nodes(query, node_type="concept")
        concepts = [
            {"id": c["id"], "name": c.get("name", "")}
            for c in concept_results[:5]
        ]
        
        # If we found a statute, get related concepts via judgments
        if statute_info.get("related"):
            for j in statute_info["related"][:2]:
                judgment_concepts = self.kg.get_related_concepts(j["id"])
                for c in judgment_concepts:
                    if not any(x["id"] == c["id"] for x in concepts):
                        concepts.append({"id": c["id"], "name": c.get("name", "")})
        
        return {"concepts": concepts[:10]}
    
    def _search_documents(
        self, 
        query: str, 
        kg_results: Dict, 
        top_k: int
    ) -> List[Dict]:
        """Search documents with KG-boosted scoring."""
        query_lower = query.lower()
        query_words = [w.strip() for w in query_lower.split() if len(w.strip()) > 2]
        
        if not query_words:
            return []
        
        # Collect judgment IDs that should be boosted from KG
        boost_ids = set()
        for concept in kg_results.get("concepts", []):
            related = self.kg.find_related_judgments(concept["id"])
            for j in related:
                boost_ids.add(j["id"])
        
        scored_docs = []
        
        for doc in self.documents:
            score = 0.0
            
            title = doc.get("title", "").lower()
            content = doc.get("content", "").lower()
            keywords = [k.lower() for k in doc.get("keywords", [])]
            statutes = " ".join(doc.get("statutes", [])).lower()
            
            for word in query_words:
                # Title match (highest weight)
                if word in title:
                    score += 0.4
                
                # Keyword match
                for kw in keywords:
                    if word in kw or kw in word:
                        score += 0.35
                        break
                
                # Statute match
                if word in statutes:
                    score += 0.3
                
                # Content match (frequency-based)
                word_count = content.count(word)
                if word_count > 0:
                    score += min(word_count * 0.02, 0.15)
            
            # KG boost: if this document is related to query concepts
            if doc.get("doc_id") in boost_ids:
                score += 0.25
            
            # Normalize
            score = min(score, 1.0)
            
            if score > 0:
                scored_docs.append({
                    "doc_id": doc.get("doc_id", ""),
                    "title": doc.get("title", ""),
                    "content": doc.get("content", "")[:500],
                    "score": round(score, 3),
                    "year": doc.get("year"),
                    "court": doc.get("court", ""),
                    "statutes": doc.get("statutes", []),
                    "keywords": doc.get("keywords", [])
                })
        
        # Sort by score
        scored_docs.sort(key=lambda x: x["score"], reverse=True)
        
        return scored_docs[:top_k]


# Singleton
_search_instance: Optional[SearchEngine] = None


def get_search_engine() -> SearchEngine:
    """Get singleton search engine instance."""
    global _search_instance
    if _search_instance is None:
        _search_instance = SearchEngine()
    return _search_instance


# For testing
if __name__ == "__main__":
    engine = SearchEngine()
    
    print("\n--- Test: 'IPC 377' ---")
    results = engine.search("IPC 377")
    print(f"Statute mapping: {results['statute_mapping']}")
    print(f"Related statutes: {results['related_statutes']}")
    print(f"Results: {len(results['results'])}")
    for r in results['results'][:2]:
        print(f"  - {r['title']} ({r['score']})")
    
    print("\n--- Test: 'medical negligence' ---")
    results = engine.search("medical negligence")
    print(f"Concepts: {results['kg_concepts']}")
    for r in results['results'][:2]:
        print(f"  - {r['title']} ({r['score']})")
    
    print("\n--- Test: 'privacy fundamental right' ---")
    results = engine.search("privacy fundamental right")
    for r in results['results'][:3]:
        print(f"  - {r['title']} ({r['score']})")
