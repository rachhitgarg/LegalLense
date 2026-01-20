"""
diagnose.py - Comprehensive diagnostics for Legal Lens components.

Tests:
1. Qdrant Cloud connection and search
2. Neo4j connection and query
3. LLM (OpenAI) connection
4. Full RAG pipeline
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_env_vars():
    """Check if all required environment variables are set."""
    print("\n[1] ENVIRONMENT VARIABLES")
    print("-" * 40)
    
    vars_to_check = [
        "QDRANT_CLOUD_URL",
        "QDRANT_API_KEY", 
        "NEO4J_URI",
        "NEO4J_USER",
        "NEO4J_PASSWORD",
        "OPENAI_API_KEY"
    ]
    
    all_set = True
    for var in vars_to_check:
        value = os.getenv(var, "NOT SET")
        if value == "NOT SET" or value.startswith("YOUR_"):
            print(f"  [X] {var}: NOT SET or placeholder")
            all_set = False
        else:
            # Mask sensitive values
            masked = value[:10] + "..." if len(value) > 15 else value
            print(f"  [OK] {var}: {masked}")
    
    return all_set


def check_qdrant():
    """Test Qdrant Cloud connection and search."""
    print("\n[2] QDRANT CLOUD")
    print("-" * 40)
    
    cloud_url = os.getenv("QDRANT_CLOUD_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    
    if not cloud_url or not api_key:
        print("  [X] Missing Qdrant credentials")
        return False
    
    try:
        from qdrant_client import QdrantClient
        
        print(f"  Connecting to {cloud_url[:50]}...")
        client = QdrantClient(url=cloud_url, api_key=api_key)
        
        # List collections
        collections = client.get_collections()
        print(f"  [OK] Connected! Collections: {[c.name for c in collections.collections]}")
        
        # Check if legal_documents exists
        if any(c.name == "legal_documents" for c in collections.collections):
            collection_info = client.get_collection("legal_documents")
            print(f"  [OK] legal_documents: {collection_info.points_count} points")
            
            # Test search (without embedding)
            from pipeline.embeddings import EmbeddingService
            print("  Loading embedding model...")
            service = EmbeddingService(cloud_url=cloud_url, api_key=api_key)
            
            print("  Searching for 'medical negligence'...")
            results = service.search("medical negligence", top_k=3)
            print(f"  [OK] Search returned {len(results)} results:")
            for r in results:
                print(f"      - {r['payload'].get('filename', r['id'])}: {r['score']:.4f}")
            return True
        else:
            print("  [X] Collection 'legal_documents' not found!")
            return False
            
    except Exception as e:
        print(f"  [X] Error: {e}")
        return False


def check_neo4j():
    """Test Neo4j connection."""
    print("\n[3] NEO4J")
    print("-" * 40)
    
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    
    if not uri or not password:
        print("  [X] Missing Neo4j credentials")
        return False
    
    try:
        from neo4j import GraphDatabase
        
        print(f"  Connecting to {uri}...")
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        with driver.session() as session:
            result = session.run("MATCH (s:Statute) RETURN count(s) as count")
            count = result.single()["count"]
            print(f"  [OK] Connected! Statute nodes: {count}")
            
            # Test mapping query
            result = session.run(
                "MATCH (old:Statute {code: 'IPC'})-[:REPLACED_BY]->(new:Statute) RETURN count(*) as count"
            )
            mappings = result.single()["count"]
            print(f"  [OK] IPC->BNS mappings: {mappings}")
        
        driver.close()
        return True
        
    except Exception as e:
        print(f"  [X] Error: {e}")
        return False


def check_openai():
    """Test OpenAI API connection."""
    print("\n[4] OPENAI LLM")
    print("-" * 40)
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key or api_key.startswith("YOUR_"):
        print("  [X] OpenAI API key not set")
        return False
    
    try:
        from openai import OpenAI
        
        print("  Testing OpenAI connection...")
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'OK' if you can hear me."}],
            max_tokens=10
        )
        
        reply = response.choices[0].message.content
        print(f"  [OK] OpenAI responded: {reply}")
        return True
        
    except Exception as e:
        print(f"  [X] Error: {e}")
        return False


def check_api_endpoint():
    """Test the FastAPI search endpoint."""
    print("\n[5] FASTAPI SEARCH ENDPOINT")
    print("-" * 40)
    
    try:
        import httpx
        
        base_url = "http://127.0.0.1:8000"
        
        # First login
        print("  Logging in...")
        login_resp = httpx.post(f"{base_url}/login", json={
            "username": "practitioner_demo",
            "password": "demo123"
        })
        
        if login_resp.status_code != 200:
            print(f"  [X] Login failed: {login_resp.status_code}")
            return False
        
        token = login_resp.json()["access_token"]
        print(f"  [OK] Got token: {token[:20]}...")
        
        # Now search
        print("  Searching via API...")
        search_resp = httpx.post(
            f"{base_url}/search",
            json={"query": "medical negligence", "top_k": 5},
            headers={"Authorization": f"Bearer {token}"},
            timeout=60.0
        )
        
        if search_resp.status_code != 200:
            print(f"  [X] Search failed: {search_resp.status_code}")
            print(f"      Response: {search_resp.text[:500]}")
            return False
        
        data = search_resp.json()
        print(f"  [OK] Search returned {len(data['results'])} results")
        for r in data['results'][:3]:
            print(f"      - {r['doc_id']}: {r['score']}")
        print(f"  LLM Response: {data['llm_response'][:100]}...")
        return True
        
    except Exception as e:
        print(f"  [X] Error: {e}")
        return False


def main():
    print("=" * 60)
    print("LEGAL LENS - DIAGNOSTICS")
    print("=" * 60)
    
    # Add parent to path
    sys.path.insert(0, str(Path(__file__).parent))
    
    results = {
        "env": check_env_vars(),
        "qdrant": check_qdrant(),
        "neo4j": check_neo4j(),
        "openai": check_openai(),
        "api": check_api_endpoint(),
    }
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for name, status in results.items():
        icon = "[OK]" if status else "[X]"
        print(f"  {icon} {name.upper()}")
    
    if all(results.values()):
        print("\nAll components working!")
    else:
        print("\nSome components have issues. Check the details above.")


if __name__ == "__main__":
    main()
