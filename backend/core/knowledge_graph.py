"""
Knowledge Graph Module for Legal Lens

Provides graph-based access to:
- Statute mappings (IPC → BNS)
- Judgment nodes with citations
- Legal concepts and relationships
"""

import json
import os
from typing import Dict, List, Optional, Any
from pathlib import Path

# Try to import networkx, fall back to simple dict-based graph if not available
try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False


class KnowledgeGraph:
    """
    Knowledge Graph for Legal Lens.
    
    Nodes: statutes, judgments, concepts
    Edges: REPLACED_BY, CITES, INTERPRETS, RELATED_TO, etc.
    """
    
    def __init__(self, kg_path: Optional[str] = None, mapping_path: Optional[str] = None):
        """
        Initialize the Knowledge Graph.
        
        Args:
            kg_path: Path to knowledge_graph.json
            mapping_path: Path to mapping.json (optional, for additional mappings)
        """
        # Default paths relative to project structure
        base_dir = Path(__file__).parent.parent.parent
        
        self.kg_path = kg_path or str(base_dir / "data" / "knowledge_graph.json")
        self.mapping_path = mapping_path or str(base_dir / "data" / "mapping.json")
        
        # Internal storage
        self.nodes: Dict[str, Dict] = {}
        self.edges: List[Dict] = []
        self.statute_mappings: Dict[str, Dict] = {}  # IPC_302 -> BNS info
        
        # NetworkX graph (if available)
        self.graph = None
        
        # Load data
        self._load_knowledge_graph()
        self._load_mappings()
        self._build_graph()
    
    def _load_knowledge_graph(self):
        """Load the knowledge graph JSON file."""
        if not os.path.exists(self.kg_path):
            print(f"Warning: KG file not found at {self.kg_path}")
            return
        
        with open(self.kg_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Index nodes by ID
        for node in data.get("nodes", []):
            self.nodes[node["id"]] = node
        
        # Store edges
        self.edges = data.get("links", [])
        
        print(f"Loaded KG: {len(self.nodes)} nodes, {len(self.edges)} edges")
    
    def _load_mappings(self):
        """Load additional statute mappings."""
        if not os.path.exists(self.mapping_path):
            return
        
        with open(self.mapping_path, 'r', encoding='utf-8') as f:
            mappings = json.load(f)
        
        for m in mappings:
            old_key = f"{m['old_code']}_{m['old_section']}"
            self.statute_mappings[old_key] = {
                "old_code": m["old_code"],
                "old_section": m["old_section"],
                "new_code": m["new_code"],
                "new_section": m["new_section"],
                "title": m.get("title", "")
            }
    
    def _build_graph(self):
        """Build NetworkX graph if available."""
        if not HAS_NETWORKX:
            return
        
        self.graph = nx.DiGraph()
        
        # Add nodes
        for node_id, node_data in self.nodes.items():
            self.graph.add_node(node_id, **node_data)
        
        # Add edges
        for edge in self.edges:
            self.graph.add_edge(
                edge["source"],
                edge["target"],
                relationship=edge.get("relationship", "RELATED_TO")
            )
    
    # =========================================================================
    # QUERY METHODS
    # =========================================================================
    
    def get_statute_mapping(self, code: str, section: str) -> Optional[Dict]:
        """
        Get the new statute (BNS) mapping for an old statute (IPC/CrPC).
        
        Args:
            code: Statute code (e.g., "IPC", "CrPC")
            section: Section number (e.g., "302", "304A")
        
        Returns:
            Mapping info or None if not found
        """
        key = f"{code}_{section}"
        
        # Check pre-loaded mappings first
        if key in self.statute_mappings:
            return self.statute_mappings[key]
        
        # Fall back to KG nodes
        old_node = self.nodes.get(key)
        if not old_node:
            return None
        
        # Find REPLACED_BY edge
        for edge in self.edges:
            if edge["source"] == key and edge.get("relationship") == "REPLACED_BY":
                new_node = self.nodes.get(edge["target"])
                if new_node:
                    return {
                        "old_code": old_node.get("code", code),
                        "old_section": old_node.get("section", section),
                        "new_code": new_node.get("code", "BNS"),
                        "new_section": new_node.get("section", ""),
                        "description": new_node.get("description", ""),
                        "title": old_node.get("description", "")
                    }
        
        return None
    
    def find_judgments_citing_statute(self, code: str, section: str) -> List[Dict]:
        """
        Find all judgments that cite a specific statute.
        
        Args:
            code: Statute code (e.g., "IPC")
            section: Section number (e.g., "377")
        
        Returns:
            List of judgment nodes
        """
        statute_id = f"{code}_{section}"
        judgments = []
        
        for edge in self.edges:
            if edge["target"] == statute_id and edge.get("relationship") == "CITES":
                judgment = self.nodes.get(edge["source"])
                if judgment and judgment.get("type") == "judgment":
                    judgments.append(judgment)
        
        return judgments
    
    def get_related_concepts(self, judgment_id: str) -> List[Dict]:
        """
        Get concepts interpreted by a judgment.
        
        Args:
            judgment_id: ID of the judgment (e.g., "navtej_johar_2018")
        
        Returns:
            List of concept nodes
        """
        concepts = []
        
        for edge in self.edges:
            if edge["source"] == judgment_id and edge.get("relationship") == "INTERPRETS":
                concept = self.nodes.get(edge["target"])
                if concept and concept.get("type") == "concept":
                    concepts.append(concept)
        
        return concepts
    
    def find_related_judgments(self, concept_id: str) -> List[Dict]:
        """
        Find judgments that interpret a specific concept.
        
        Args:
            concept_id: ID of the concept (e.g., "right_to_privacy")
        
        Returns:
            List of judgment nodes
        """
        judgments = []
        
        for edge in self.edges:
            if edge["target"] == concept_id and edge.get("relationship") == "INTERPRETS":
                judgment = self.nodes.get(edge["source"])
                if judgment and judgment.get("type") == "judgment":
                    judgments.append(judgment)
        
        return judgments
    
    def search_nodes(self, query: str, node_type: Optional[str] = None) -> List[Dict]:
        """
        Search nodes by text matching.
        
        Args:
            query: Search query
            node_type: Optional filter by node type (statute, judgment, concept)
        
        Returns:
            List of matching nodes with scores
        """
        query_lower = query.lower()
        results = []
        
        for node_id, node in self.nodes.items():
            if node_type and node.get("type") != node_type:
                continue
            
            score = 0.0
            
            # Check various fields
            if query_lower in node_id.lower():
                score += 0.5
            
            if query_lower in node.get("title", "").lower():
                score += 0.4
            
            if query_lower in node.get("description", "").lower():
                score += 0.3
            
            if query_lower in node.get("summary", "").lower():
                score += 0.3
            
            if query_lower in node.get("name", "").lower():
                score += 0.4
            
            # Check section numbers
            if node.get("section") and query_lower in str(node.get("section")).lower():
                score += 0.5
            
            if score > 0:
                results.append({**node, "_score": score})
        
        # Sort by score
        results.sort(key=lambda x: x["_score"], reverse=True)
        return results
    
    def multi_hop_search(self, start_id: str, max_hops: int = 2) -> Dict[str, Any]:
        """
        Perform multi-hop traversal from a starting node.
        
        Args:
            start_id: Starting node ID
            max_hops: Maximum number of hops
        
        Returns:
            Dictionary with found nodes organized by hop distance
        """
        if HAS_NETWORKX and self.graph:
            return self._networkx_multi_hop(start_id, max_hops)
        
        return self._simple_multi_hop(start_id, max_hops)
    
    def _networkx_multi_hop(self, start_id: str, max_hops: int) -> Dict[str, Any]:
        """Multi-hop using NetworkX."""
        result = {"start": self.nodes.get(start_id), "hops": {}}
        
        if start_id not in self.graph:
            return result
        
        for hop in range(1, max_hops + 1):
            # Get nodes at this hop distance
            try:
                paths = nx.single_source_shortest_path_length(
                    self.graph, start_id, cutoff=hop
                )
                nodes_at_hop = [
                    self.nodes[n] for n, d in paths.items() 
                    if d == hop and n in self.nodes
                ]
                result["hops"][hop] = nodes_at_hop
            except nx.NetworkXError:
                break
        
        return result
    
    def _simple_multi_hop(self, start_id: str, max_hops: int) -> Dict[str, Any]:
        """Simple multi-hop without NetworkX."""
        result = {"start": self.nodes.get(start_id), "hops": {}}
        visited = {start_id}
        current_level = {start_id}
        
        for hop in range(1, max_hops + 1):
            next_level = set()
            
            for node_id in current_level:
                for edge in self.edges:
                    if edge["source"] == node_id and edge["target"] not in visited:
                        next_level.add(edge["target"])
                    if edge["target"] == node_id and edge["source"] not in visited:
                        next_level.add(edge["source"])
            
            if next_level:
                result["hops"][hop] = [
                    self.nodes[n] for n in next_level if n in self.nodes
                ]
                visited.update(next_level)
                current_level = next_level
            else:
                break
        
        return result
    
    def get_all_judgments(self) -> List[Dict]:
        """Get all judgment nodes."""
        return [n for n in self.nodes.values() if n.get("type") == "judgment"]
    
    def get_all_statutes(self) -> List[Dict]:
        """Get all statute nodes (both old and new)."""
        return [
            n for n in self.nodes.values() 
            if n.get("type") in ["old_statute", "new_statute", "statute_reference"]
        ]
    
    def get_all_concepts(self) -> List[Dict]:
        """Get all concept nodes."""
        return [n for n in self.nodes.values() if n.get("type") == "concept"]


# Singleton instance
_kg_instance: Optional[KnowledgeGraph] = None


def get_knowledge_graph() -> KnowledgeGraph:
    """Get the singleton KG instance."""
    global _kg_instance
    if _kg_instance is None:
        _kg_instance = KnowledgeGraph()
    return _kg_instance


# For testing
if __name__ == "__main__":
    kg = KnowledgeGraph()
    
    print("\n--- Test: Statute Mapping ---")
    mapping = kg.get_statute_mapping("IPC", "302")
    print(f"IPC 302 -> {mapping}")
    
    print("\n--- Test: Judgments citing IPC 377 ---")
    judgments = kg.find_judgments_citing_statute("IPC", "377")
    for j in judgments:
        print(f"  - {j.get('title')}")
    
    print("\n--- Test: Search 'privacy' ---")
    results = kg.search_nodes("privacy")
    for r in results[:3]:
        print(f"  - {r.get('id')}: {r.get('title', r.get('name', ''))}")
    
    print("\n--- Test: Multi-hop from navtej_johar_2018 ---")
    hops = kg.multi_hop_search("navtej_johar_2018", max_hops=2)
    for hop_num, nodes in hops.get("hops", {}).items():
        print(f"  Hop {hop_num}: {[n.get('id') for n in nodes]}")
