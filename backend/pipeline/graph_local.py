"""
graph_local.py - NetworkX-based Knowledge Graph for statute mappings.

No external database required! Uses JSON file for persistence.
"""

import json
import networkx as nx
from pathlib import Path
from typing import Optional, List, Dict


class LocalKnowledgeGraph:
    """
    Local Knowledge Graph using NetworkX.
    
    Stores IPC to BNS mappings and legal relationships.
    Persists to JSON file - no external database needed.
    """
    
    def __init__(self, data_dir: str = "../data"):
        self.data_dir = Path(data_dir)
        self.graph = nx.DiGraph()
        self.graph_file = self.data_dir / "knowledge_graph.json"
        
        # Load existing graph or create new
        if self.graph_file.exists():
            self._load_graph()
        else:
            self._initialize_graph()
    
    def _initialize_graph(self):
        """Initialize graph with mapping.json data."""
        mapping_file = self.data_dir / "mapping.json"
        
        if mapping_file.exists():
            with open(mapping_file, "r", encoding="utf-8") as f:
                mappings = json.load(f)
            
            for item in mappings:
                old_code = item.get("old_code", "IPC")
                old_section = item.get("old_section", "")
                new_code = item.get("new_code", "BNS")
                new_section = item.get("new_section", "")
                description = item.get("description", "")
                
                # Create nodes
                old_node = f"{old_code}_{old_section}"
                new_node = f"{new_code}_{new_section}"
                
                self.graph.add_node(old_node, 
                    code=old_code, 
                    section=old_section,
                    description=description,
                    type="old_statute"
                )
                
                self.graph.add_node(new_node,
                    code=new_code,
                    section=new_section,
                    description=description,
                    type="new_statute"
                )
                
                # Create relationship
                self.graph.add_edge(old_node, new_node, 
                    relationship="REPLACED_BY"
                )
            
            self._save_graph()
    
    def _load_graph(self):
        """Load graph from JSON file."""
        with open(self.graph_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.graph = nx.node_link_graph(data)
    
    def _save_graph(self):
        """Save graph to JSON file."""
        data = nx.node_link_data(self.graph)
        with open(self.graph_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    
    def get_mapping(self, old_code: str, old_section: str) -> Optional[Dict]:
        """Get the new statute that replaced an old statute."""
        old_node = f"{old_code}_{old_section}"
        
        if old_node not in self.graph:
            return None
        
        # Find replacement
        successors = list(self.graph.successors(old_node))
        if not successors:
            return None
        
        new_node = successors[0]
        return {
            "old": self.graph.nodes[old_node],
            "new": self.graph.nodes[new_node],
            "mapping": f"{old_code} Section {old_section} → {self.graph.nodes[new_node]['code']} Section {self.graph.nodes[new_node]['section']}"
        }
    
    def search_statutes(self, query: str) -> List[Dict]:
        """Search for statutes matching query."""
        results = []
        query_lower = query.lower()
        
        for node, data in self.graph.nodes(data=True):
            # Search in section number and description
            section = str(data.get("section", ""))
            description = data.get("description", "").lower()
            code = data.get("code", "")
            
            if query_lower in section or query_lower in description or query_lower in code.lower():
                results.append({
                    "node": node,
                    "code": code,
                    "section": section,
                    "description": data.get("description", ""),
                    "type": data.get("type", "")
                })
        
        return results
    
    def get_all_mappings(self) -> List[Dict]:
        """Get all statute mappings."""
        mappings = []
        
        for old_node, new_node, data in self.graph.edges(data=True):
            if data.get("relationship") == "REPLACED_BY":
                old_data = self.graph.nodes[old_node]
                new_data = self.graph.nodes[new_node]
                
                mappings.append({
                    "old_code": old_data.get("code"),
                    "old_section": old_data.get("section"),
                    "new_code": new_data.get("code"),
                    "new_section": new_data.get("section"),
                    "description": old_data.get("description", "")
                })
        
        return mappings
    
    def add_mapping(self, old_code: str, old_section: str, 
                   new_code: str, new_section: str, description: str = ""):
        """Add a new statute mapping."""
        old_node = f"{old_code}_{old_section}"
        new_node = f"{new_code}_{new_section}"
        
        self.graph.add_node(old_node, 
            code=old_code, section=old_section, 
            description=description, type="old_statute"
        )
        self.graph.add_node(new_node,
            code=new_code, section=new_section,
            description=description, type="new_statute"
        )
        self.graph.add_edge(old_node, new_node, relationship="REPLACED_BY")
        
        self._save_graph()
    
    def get_stats(self) -> Dict:
        """Get graph statistics."""
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "old_statutes": len([n for n, d in self.graph.nodes(data=True) if d.get("type") == "old_statute"]),
            "new_statutes": len([n for n, d in self.graph.nodes(data=True) if d.get("type") == "new_statute"]),
        }


# Singleton instance
_kg_instance = None

def get_knowledge_graph(data_dir: str = "../data") -> LocalKnowledgeGraph:
    """Get or create the knowledge graph instance."""
    global _kg_instance
    if _kg_instance is None:
        _kg_instance = LocalKnowledgeGraph(data_dir)
    return _kg_instance
