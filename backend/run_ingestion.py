"""
run_ingestion.py - Run the full data ingestion pipeline.

This script:
1. Connects to Qdrant Cloud
2. Loads documents from the data folder
3. Generates embeddings using BGE-M3
4. Stores embeddings in Qdrant
5. Loads IPC↔BNS mapping into Neo4j (if available)
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from pipeline.ingest import load_documents
from pipeline.embeddings import EmbeddingService


def main():
    print("=" * 60)
    print("LEGAL LENS - Data Ingestion Pipeline")
    print("=" * 60)
    
    # Get Qdrant Cloud credentials from environment
    cloud_url = os.getenv("QDRANT_CLOUD_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    
    if not cloud_url or not api_key or "YOUR_" in cloud_url:
        print("[ERROR] Qdrant Cloud credentials not set in .env file")
        return
    
    print(f"\n[1/4] Connecting to Qdrant Cloud...")
    try:
        embedding_service = EmbeddingService(
            cloud_url=cloud_url,
            api_key=api_key,
            model_name="BAAI/bge-m3"
        )
        print("[OK] Connected to Qdrant Cloud successfully!")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Qdrant: {e}")
        return
    
    print(f"\n[2/4] Loading documents from data folder...")
    data_dir = os.getenv("DATA_DIR", "../data")
    
    # Also check the original data location
    original_data = Path(__file__).parent.parent.parent.parent / "data"
    if original_data.exists():
        data_dir = str(original_data)
    
    try:
        documents = load_documents(data_dir)
        print(f"[OK] Loaded {len(documents)} documents")
        for doc in documents[:5]:
            content_len = len(doc.get("content", ""))
            print(f"    - {doc['filename']}: {content_len} chars")
    except FileNotFoundError as e:
        print(f"[WARNING] Data directory not found: {data_dir}")
        print("[INFO] Creating sample document for testing...")
        documents = [{
            "id": "sample_1",
            "filename": "sample_judgment.txt",
            "content": "This is a sample legal judgment about medical negligence...",
            "source_type": ".txt"
        }]
    
    if not documents:
        print("[WARNING] No documents found. Creating sample for testing...")
        documents = [{
            "id": "sample_1",
            "filename": "sample_judgment.txt",
            "content": "This is a sample legal judgment about medical negligence involving Section 304A of IPC which has been replaced by Section 106 of BNS.",
            "source_type": ".txt"
        }]
    
    print(f"\n[3/4] Generating embeddings and uploading to Qdrant...")
    try:
        embedding_service.embed_documents(documents)
        print(f"[OK] Uploaded {len(documents)} documents to Qdrant Cloud!")
    except Exception as e:
        print(f"[ERROR] Failed to upload embeddings: {e}")
        return
    
    print(f"\n[4/4] Testing search...")
    try:
        results = embedding_service.search("medical negligence", top_k=3)
        print(f"[OK] Search returned {len(results)} results")
        for r in results:
            print(f"    - Score: {r['score']:.4f} | {r['payload'].get('filename', 'N/A')}")
    except Exception as e:
        print(f"[ERROR] Search failed: {e}")
        return
    
    print("\n" + "=" * 60)
    print("✅ INGESTION COMPLETE!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Start Neo4j and run mapping_loader.py")
    print("2. Start the backend: uvicorn api.main:app --reload")
    print("3. Start the frontend: npm run dev")
    print("4. Open http://localhost:5173")


if __name__ == "__main__":
    main()
