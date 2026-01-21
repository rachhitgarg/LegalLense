"""
graph_local.py - NetworkX-based Knowledge Graph for Legal Lens.

Stores:
1. Statute mappings (IPC → BNS)
2. Judgment documents linked to statutes they cite
3. Legal concepts and relationships

No external database required! Uses JSON file for persistence.
"""

import json
import networkx as nx
from pathlib import Path
from typing import Optional, List, Dict


class LocalKnowledgeGraph:
    """
    Local Knowledge Graph using NetworkX.
    
    Node Types:
    - old_statute: IPC/CrPC sections (e.g., IPC_302)
    - new_statute: BNS/BNSS sections (e.g., BNS_101)
    - judgment: Court cases (e.g., jacob_mathew_2005)
    - concept: Legal concepts (e.g., medical_negligence)
    
    Edge Types:
    - REPLACED_BY: Old statute → New statute
    - CITES: Judgment → Statute
    - INTERPRETS: Judgment → Concept
    - RELATED_TO: Concept → Concept
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
        """Initialize graph with mappings and judgments."""
        self._add_statute_mappings()
        self._add_judgments()
        self._add_concepts()
        self._save_graph()
    
    def _add_statute_mappings(self):
        """Add IPC → BNS statute mappings."""
        # Core mappings (can be loaded from mapping.json if available)
        mappings = [
            {"old": ("IPC", "302"), "new": ("BNS", "101"), "desc": "Murder"},
            {"old": ("IPC", "304"), "new": ("BNS", "105"), "desc": "Culpable homicide not amounting to murder"},
            {"old": ("IPC", "304A"), "new": ("BNS", "106"), "desc": "Death by negligence"},
            {"old": ("IPC", "307"), "new": ("BNS", "109"), "desc": "Attempt to murder"},
            {"old": ("IPC", "376"), "new": ("BNS", "63"), "desc": "Rape"},
            {"old": ("IPC", "377"), "new": ("BNS", "None"), "desc": "Unnatural offences (partially decriminalized)"},
            {"old": ("IPC", "420"), "new": ("BNS", "316"), "desc": "Cheating and dishonestly inducing delivery"},
            {"old": ("IPC", "498A"), "new": ("BNS", "84"), "desc": "Cruelty by husband or relatives"},
            {"old": ("IPC", "499"), "new": ("BNS", "354"), "desc": "Defamation"},
            {"old": ("IPC", "506"), "new": ("BNS", "349"), "desc": "Criminal intimidation"},
        ]
        
        # Load from mapping.json if exists
        mapping_file = self.data_dir / "mapping.json"
        if mapping_file.exists():
            with open(mapping_file, "r", encoding="utf-8") as f:
                file_mappings = json.load(f)
                for item in file_mappings:
                    mappings.append({
                        "old": (item.get("old_code", "IPC"), item.get("old_section", "")),
                        "new": (item.get("new_code", "BNS"), item.get("new_section", "")),
                        "desc": item.get("description", "")
                    })
        
        for m in mappings:
            old_node = f"{m['old'][0]}_{m['old'][1]}"
            new_node = f"{m['new'][0]}_{m['new'][1]}"
            
            self.graph.add_node(old_node,
                type="old_statute",
                code=m['old'][0],
                section=m['old'][1],
                description=m['desc']
            )
            
            self.graph.add_node(new_node,
                type="new_statute", 
                code=m['new'][0],
                section=m['new'][1],
                description=m['desc']
            )
            
            self.graph.add_edge(old_node, new_node, relationship="REPLACED_BY")
    
    def _add_judgments(self):
        """Add landmark judgments and link to cited statutes."""
        judgments = [
            {
                "id": "jacob_mathew_2005",
                "title": "Jacob Mathew vs State of Punjab",
                "year": 2005,
                "court": "Supreme Court of India",
                "summary": "Established guidelines for medical negligence prosecution",
                "cites": ["IPC_304A"],
                "concepts": ["medical_negligence", "professional_liability"]
            },
            {
                "id": "kesavananda_bharati_1973",
                "title": "Kesavananda Bharati vs State of Kerala",
                "year": 1973,
                "court": "Supreme Court of India",
                "summary": "Established Basic Structure Doctrine limiting Parliament's amending power",
                "cites": ["Article_368", "Article_13"],
                "concepts": ["basic_structure", "constitutional_amendment"]
            },
            {
                "id": "navtej_johar_2018",
                "title": "Navtej Singh Johar vs Union of India",
                "year": 2018,
                "court": "Supreme Court of India",
                "summary": "Decriminalized consensual homosexual acts by reading down Section 377",
                "cites": ["IPC_377", "Article_14", "Article_21"],
                "concepts": ["right_to_privacy", "lgbtq_rights", "equality"]
            },
            {
                "id": "puttaswamy_2017",
                "title": "K.S. Puttaswamy vs Union of India",
                "year": 2017,
                "court": "Supreme Court of India",
                "summary": "Right to Privacy declared a fundamental right under Article 21",
                "cites": ["Article_21", "Article_14", "Article_19"],
                "concepts": ["right_to_privacy", "data_protection", "fundamental_rights"]
            },
            {
                "id": "vineeta_sharma_2020",
                "title": "Vineeta Sharma vs Rakesh Sharma",
                "year": 2020,
                "court": "Supreme Court of India",
                "summary": "Daughters have equal coparcenary rights by birth",
                "cites": ["Hindu_Succession_Act"],
                "concepts": ["gender_equality", "property_rights", "inheritance"]
            },
            {
                "id": "maneka_gandhi_1978",
                "title": "Maneka Gandhi vs Union of India",
                "year": 1978,
                "court": "Supreme Court of India",
                "summary": "Expanded Article 21 to include right to live with dignity",
                "cites": ["Article_21", "Article_14", "Article_19"],
                "concepts": ["right_to_life", "due_process", "natural_justice"]
            },
            {
                "id": "vishaka_1997",
                "title": "Vishaka vs State of Rajasthan",
                "year": 1997,
                "court": "Supreme Court of India",
                "summary": "Laid down guidelines for prevention of sexual harassment at workplace",
                "cites": ["Article_14", "Article_19", "Article_21"],
                "concepts": ["sexual_harassment", "womens_rights", "workplace_safety"]
            }
        ]
        
        for j in judgments:
            # Add judgment node
            self.graph.add_node(j["id"],
                type="judgment",
                title=j["title"],
                year=j["year"],
                court=j["court"],
                summary=j["summary"]
            )
            
            # Add CITES edges to statutes
            for statute in j.get("cites", []):
                # Create statute node if doesn't exist
                if statute not in self.graph:
                    self.graph.add_node(statute,
                        type="statute_reference",
                        code=statute.split("_")[0] if "_" in statute else statute,
                        section=statute.split("_")[1] if "_" in statute else ""
                    )
                
                self.graph.add_edge(j["id"], statute, relationship="CITES")
            
            # Add INTERPRETS edges to concepts
            for concept in j.get("concepts", []):
                if concept not in self.graph:
                    self.graph.add_node(concept, type="concept", name=concept.replace("_", " ").title())
                
                self.graph.add_edge(j["id"], concept, relationship="INTERPRETS")
    
    def _add_concepts(self):
        """Add legal concepts and their relationships."""
        concept_relations = [
            ("medical_negligence", "professional_liability", "SUBSET_OF"),
            ("right_to_privacy", "fundamental_rights", "PART_OF"),
            ("right_to_life", "fundamental_rights", "PART_OF"),
            ("equality", "fundamental_rights", "PART_OF"),
            ("due_process", "natural_justice", "RELATED_TO"),
            ("gender_equality", "equality", "SUBSET_OF"),
            ("lgbtq_rights", "equality", "RELATED_TO"),
            ("data_protection", "right_to_privacy", "SUBSET_OF"),
        ]
        
        for c1, c2, rel in concept_relations:
            if c1 not in self.graph:
                self.graph.add_node(c1, type="concept", name=c1.replace("_", " ").title())
            if c2 not in self.graph:
                self.graph.add_node(c2, type="concept", name=c2.replace("_", " ").title())
            
            self.graph.add_edge(c1, c2, relationship=rel)
    
    def _load_graph(self):
        """Load graph from JSON file."""
        with open(self.graph_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.graph = nx.node_link_graph(data)
    
    def _save_graph(self):
        """Save graph to JSON file."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        data = nx.node_link_data(self.graph)
        with open(self.graph_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Query Methods
    # ─────────────────────────────────────────────────────────────────────────
    
    def get_mapping(self, old_code: str, old_section: str) -> Optional[Dict]:
        """Get the new statute that replaced an old statute."""
        old_node = f"{old_code}_{old_section}"
        
        if old_node not in self.graph:
            return None
        
        for _, new_node, data in self.graph.out_edges(old_node, data=True):
            if data.get("relationship") == "REPLACED_BY":
                new_data = self.graph.nodes[new_node]
                return {
                    "old": self.graph.nodes[old_node],
                    "new": new_data,
                    "mapping": f"{old_code} Section {old_section} → {new_data.get('code', '')} Section {new_data.get('section', '')}"
                }
        return None
    
    def get_judgments_citing(self, statute: str) -> List[Dict]:
        """Get all judgments that cite a specific statute."""
        results = []
        
        for source, target, data in self.graph.edges(data=True):
            if target == statute and data.get("relationship") == "CITES":
                node_data = self.graph.nodes[source]
                if node_data.get("type") == "judgment":
                    results.append({
                        "id": source,
                        **node_data
                    })
        
        return results
    
    def get_statutes_cited_by(self, judgment_id: str) -> List[Dict]:
        """Get all statutes cited by a judgment."""
        if judgment_id not in self.graph:
            return []
        
        results = []
        for _, target, data in self.graph.out_edges(judgment_id, data=True):
            if data.get("relationship") == "CITES":
                results.append({
                    "statute": target,
                    **self.graph.nodes[target]
                })
        
        return results
    
    def get_related_judgments(self, judgment_id: str) -> List[Dict]:
        """Get judgments related through shared concepts or statutes."""
        if judgment_id not in self.graph:
            return []
        
        # Get concepts and statutes cited by this judgment
        cited = set()
        for _, target, data in self.graph.out_edges(judgment_id, data=True):
            if data.get("relationship") in ["CITES", "INTERPRETS"]:
                cited.add(target)
        
        # Find other judgments citing same concepts/statutes
        related = set()
        for node, attrs in self.graph.nodes(data=True):
            if attrs.get("type") == "judgment" and node != judgment_id:
                for _, target, _ in self.graph.out_edges(node, data=True):
                    if target in cited:
                        related.add(node)
                        break
        
        return [{"id": j, **self.graph.nodes[j]} for j in related]
    
    def search_statutes(self, query: str) -> List[Dict]:
        """Search for statutes matching query."""
        results = []
        query_lower = query.lower()
        
        for node, data in self.graph.nodes(data=True):
            if data.get("type") in ["old_statute", "new_statute", "statute_reference"]:
                section = str(data.get("section", ""))
                description = data.get("description", "").lower()
                code = data.get("code", "")
                
                if query_lower in section or query_lower in description or query_lower in code.lower() or query_lower in node.lower():
                    results.append({"node": node, **data})
        
        return results
    
    def search_judgments(self, query: str) -> List[Dict]:
        """Search for judgments matching query."""
        results = []
        query_lower = query.lower()
        
        for node, data in self.graph.nodes(data=True):
            if data.get("type") == "judgment":
                title = data.get("title", "").lower()
                summary = data.get("summary", "").lower()
                
                if query_lower in title or query_lower in summary or query_lower in node:
                    results.append({"id": node, **data})
        
        return results
    
    def get_stats(self) -> Dict:
        """Get graph statistics."""
        node_types = {}
        edge_types = {}
        
        for _, data in self.graph.nodes(data=True):
            t = data.get("type", "unknown")
            node_types[t] = node_types.get(t, 0) + 1
        
        for _, _, data in self.graph.edges(data=True):
            r = data.get("relationship", "unknown")
            edge_types[r] = edge_types.get(r, 0) + 1
        
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "node_types": node_types,
            "edge_types": edge_types
        }
    
    def visualize_subgraph(self, node_id: str, depth: int = 2) -> Dict:
        """Get a subgraph around a node for visualization."""
        if node_id not in self.graph:
            return {"nodes": [], "edges": []}
        
        # BFS to get nearby nodes
        nodes = {node_id}
        frontier = {node_id}
        
        for _ in range(depth):
            new_frontier = set()
            for n in frontier:
                new_frontier.update(self.graph.successors(n))
                new_frontier.update(self.graph.predecessors(n))
            nodes.update(new_frontier)
            frontier = new_frontier
        
        # Build response
        node_list = []
        for n in nodes:
            node_list.append({"id": n, **self.graph.nodes[n]})
        
        edge_list = []
        for u, v, data in self.graph.edges(data=True):
            if u in nodes and v in nodes:
                edge_list.append({"source": u, "target": v, **data})
        
        return {"nodes": node_list, "edges": edge_list}


# Singleton instance
_kg_instance = None

def get_knowledge_graph(data_dir: str = "../data") -> LocalKnowledgeGraph:
    """Get or create the knowledge graph instance."""
    global _kg_instance
    if _kg_instance is None:
        _kg_instance = LocalKnowledgeGraph(data_dir)
    return _kg_instance
