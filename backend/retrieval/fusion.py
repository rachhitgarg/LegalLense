"""
fusion.py - Multi-source retrieval fusion module.

Combines results from:
1. Vector similarity search (Qdrant / BGE-M3)
2. Keyword search (Elasticsearch) - optional fallback
3. Graph traversal (Neo4j) - citation chains, statute mappings

Uses weighted score fusion to produce a final ranked list.
"""

from typing import Optional
from dataclasses import dataclass


@dataclass
class RetrievalResult:
    """A single retrieval result with source provenance."""
    doc_id: str
    content: str
    score: float
    source: str  # "vector", "keyword", "graph"
    metadata: dict


class FusionRetriever:
    """
    Fuses results from multiple retrieval sources.
    
    Default weights:
    - Vector: 0.5 (semantic similarity)
    - Keyword: 0.3 (exact match)
    - Graph: 0.2 (relationship-based)
    """
    
    def __init__(
        self,
        embedding_service=None,
        graph_builder=None,
        vector_weight: float = 0.5,
        keyword_weight: float = 0.3,
        graph_weight: float = 0.2,
    ):
        self.embedding_service = embedding_service
        self.graph_builder = graph_builder
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self.graph_weight = graph_weight
    
    def search_vector(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        """Search using vector similarity."""
        if not self.embedding_service:
            return []
        
        results = self.embedding_service.search(query, top_k=top_k)
        return [
            RetrievalResult(
                doc_id=r["payload"].get("doc_id", str(r["id"])),
                content=r["payload"].get("content_preview", ""),
                score=r["score"],
                source="vector",
                metadata=r["payload"],
            )
            for r in results
        ]
    
    def search_keyword(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        """Search using keyword matching (Elasticsearch)."""
        # TODO: Implement Elasticsearch integration
        # For now, return empty list
        return []
    
    def search_graph(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        """Search using graph traversal (citation chains, mappings)."""
        if not self.graph_builder:
            return []
        
        # Simple heuristic: extract section numbers from query
        # and look up mappings
        results = []
        
        # Check for IPC section references
        import re
        ipc_matches = re.findall(r"IPC\s*(?:Section\s*)?(\d+[A-Z]?)", query, re.IGNORECASE)
        for section in ipc_matches:
            mapping = self.graph_builder.get_bns_mapping(section)
            if mapping:
                results.append(
                    RetrievalResult(
                        doc_id=f"mapping_ipc_{section}",
                        content=f"IPC Section {section} ({mapping['old'].get('title', '')}) is replaced by BNS Section {mapping['new'].get('section', '')} ({mapping['new'].get('title', '')}). Effective: {mapping.get('effective_date', '2024-07-01')}",
                        score=1.0,
                        source="graph",
                        metadata=mapping,
                    )
                )
        
        return results[:top_k]
    
    def fuse(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        """
        Fuse results from all sources using weighted scoring.
        
        Returns deduplicated, ranked results.
        """
        vector_results = self.search_vector(query, top_k=top_k * 2)
        keyword_results = self.search_keyword(query, top_k=top_k * 2)
        graph_results = self.search_graph(query, top_k=top_k)
        
        # Apply weights
        for r in vector_results:
            r.score *= self.vector_weight
        for r in keyword_results:
            r.score *= self.keyword_weight
        for r in graph_results:
            r.score *= self.graph_weight
        
        # Combine and deduplicate by doc_id
        all_results = vector_results + keyword_results + graph_results
        seen = {}
        for r in all_results:
            if r.doc_id not in seen or r.score > seen[r.doc_id].score:
                seen[r.doc_id] = r
        
        # Sort by score descending
        fused = sorted(seen.values(), key=lambda x: x.score, reverse=True)
        
        return fused[:top_k]
    
    def build_context(self, results: list[RetrievalResult], max_chars: int = 8000) -> str:
        """Build a context string from retrieval results for LLM."""
        context_parts = []
        total_chars = 0
        
        for i, r in enumerate(results):
            entry = f"[{i+1}] Source: {r.source} | ID: {r.doc_id}\n{r.content}\n"
            if total_chars + len(entry) > max_chars:
                break
            context_parts.append(entry)
            total_chars += len(entry)
        
        return "\n---\n".join(context_parts)


if __name__ == "__main__":
    fusion = FusionRetriever()
    print("Fusion retriever initialized.")
