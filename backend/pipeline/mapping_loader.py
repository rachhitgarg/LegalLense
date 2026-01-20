"""
mapping_loader.py - Load IPC↔BNS mapping from JSON into Neo4j.

Reads the mapping JSON file from data/ folder and creates Statute nodes
with REPLACED_BY relationships.
"""

import json
from pathlib import Path
from .graph_builder import GraphBuilder


def load_mapping_json(mapping_file: str = "data/mapping.json") -> list[dict]:
    """Load the IPC to BNS mapping from JSON file."""
    path = Path(mapping_file)
    if not path.exists():
        raise FileNotFoundError(f"Mapping file not found: {mapping_file}")
    
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Expected format: list of objects with ipc_section, bns_section, title, effective_date
    return data


def populate_mapping_graph(
    mapping_data: list[dict],
    graph_builder: GraphBuilder,
    effective_date: str = "2024-07-01",
):
    """
    Populate Neo4j with statute nodes and REPLACED_BY relationships.
    
    Expected mapping_data format:
    [
        {
            "old_code": "IPC",
            "old_section": "302",
            "new_code": "BNS",
            "new_section": "103",
            "title": "Punishment for murder"
        },
        ...
    ]
    """
    for item in mapping_data:
        old_code = item.get("old_code", "IPC")
        old_section = str(item.get("old_section", ""))
        new_code = item.get("new_code", "BNS")
        new_section = str(item.get("new_section", ""))
        title = item.get("title", "")
        
        if not old_section or not new_section:
            continue
        
        # Create old statute node (marked inactive)
        graph_builder.create_statute_node(
            code=old_code,
            section=old_section,
            title=title,
            is_active=False,
        )
        
        # Create new statute node (active)
        graph_builder.create_statute_node(
            code=new_code,
            section=new_section,
            title=title,
            is_active=True,
        )
        
        # Create REPLACED_BY relationship
        graph_builder.create_replaced_by_relationship(
            old_code=old_code,
            old_section=old_section,
            new_code=new_code,
            new_section=new_section,
            effective_date=effective_date,
        )


def main():
    """Load mapping and populate graph."""
    mapping_data = load_mapping_json()
    print(f"Loaded {len(mapping_data)} mapping entries.")
    
    builder = GraphBuilder()
    try:
        populate_mapping_graph(mapping_data, builder)
        print("Mapping graph populated successfully.")
    finally:
        builder.close()


if __name__ == "__main__":
    main()
