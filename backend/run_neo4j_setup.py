"""
run_neo4j_setup.py - Test Neo4j connection and load IPC to BNS mapping.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables  
load_dotenv()

def test_connection():
    """Test Neo4j connection."""
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "legal_lens_2024")
    
    print(f"Connecting to Neo4j at {uri}...")
    
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            result = session.run("RETURN 'Connected!' as message")
            record = result.single()
            print(f"[OK] {record['message']}")
        return driver
    except Exception as e:
        print(f"[ERROR] Failed to connect: {e}")
        return None


def load_mapping(driver, mapping_file="data/mapping.json"):
    """Load IPC to BNS mapping into Neo4j."""
    # Find the mapping file
    project_root = Path(__file__).parent.parent
    mapping_path = project_root / "data" / "mapping.json"
    
    if not mapping_path.exists():
        # Try alternative path
        mapping_path = Path(__file__).parent / "data" / "mapping.json"
    
    if not mapping_path.exists():
        print(f"[WARNING] Mapping file not found at {mapping_path}")
        # Use embedded data
        mapping_data = [
            {"old_code": "IPC", "old_section": "299", "new_code": "BNS", "new_section": "100", "title": "Culpable homicide"},
            {"old_code": "IPC", "old_section": "300", "new_code": "BNS", "new_section": "101", "title": "Murder"},
            {"old_code": "IPC", "old_section": "302", "new_code": "BNS", "new_section": "103", "title": "Punishment for murder"},
            {"old_code": "IPC", "old_section": "304A", "new_code": "BNS", "new_section": "106", "title": "Causing death by negligence"},
            {"old_code": "CrPC", "old_section": "154", "new_code": "BNSS", "new_section": "173", "title": "Registration of FIR"},
        ]
    else:
        print(f"[OK] Loading mapping from {mapping_path}")
        with open(mapping_path, "r", encoding="utf-8") as f:
            mapping_data = json.load(f)
    
    print(f"[OK] Found {len(mapping_data)} mapping entries")
    
    with driver.session() as session:
        for item in mapping_data:
            old_code = item.get("old_code", "IPC")
            old_section = str(item.get("old_section", ""))
            new_code = item.get("new_code", "BNS")
            new_section = str(item.get("new_section", ""))
            title = item.get("title", "")
            
            # Create old statute node
            session.run(
                """
                MERGE (s:Statute {code: $code, section: $section})
                SET s.title = $title, s.is_active = false
                """,
                code=old_code, section=old_section, title=title
            )
            
            # Create new statute node
            session.run(
                """
                MERGE (s:Statute {code: $code, section: $section})
                SET s.title = $title, s.is_active = true
                """,
                code=new_code, section=new_section, title=title
            )
            
            # Create REPLACED_BY relationship
            session.run(
                """
                MATCH (old:Statute {code: $old_code, section: $old_section})
                MATCH (new:Statute {code: $new_code, section: $new_section})
                MERGE (old)-[r:REPLACED_BY]->(new)
                SET r.effective_date = '2024-07-01'
                """,
                old_code=old_code, old_section=old_section,
                new_code=new_code, new_section=new_section
            )
            
            print(f"    {old_code} {old_section} -> {new_code} {new_section}: {title}")
    
    print(f"[OK] Loaded {len(mapping_data)} mappings into Neo4j!")


def verify_data(driver):
    """Verify the data was loaded correctly."""
    with driver.session() as session:
        # Count nodes
        result = session.run("MATCH (s:Statute) RETURN count(s) as count")
        count = result.single()["count"]
        print(f"[OK] Total Statute nodes: {count}")
        
        # Count relationships
        result = session.run("MATCH ()-[r:REPLACED_BY]->() RETURN count(r) as count")
        count = result.single()["count"]
        print(f"[OK] Total REPLACED_BY relationships: {count}")
        
        # Test a query
        print("\n[TEST] Query: What replaced IPC 304A?")
        result = session.run(
            """
            MATCH (old:Statute {code: 'IPC', section: '304A'})-[r:REPLACED_BY]->(new:Statute)
            RETURN old.title as old_title, new.code as new_code, new.section as new_section
            """
        )
        for record in result:
            print(f"    Answer: BNS Section {record['new_section']} ({record['old_title']})")


def main():
    print("=" * 60)
    print("LEGAL LENS - Neo4j Setup")
    print("=" * 60)
    
    driver = test_connection()
    if not driver:
        print("\nMake sure Neo4j is running and credentials are correct in .env")
        return
    
    print("\nLoading IPC to BNS mapping...")
    load_mapping(driver)
    
    print("\nVerifying data...")
    verify_data(driver)
    
    driver.close()
    
    print("\n" + "=" * 60)
    print("Neo4j setup complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
