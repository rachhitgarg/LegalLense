"""
load_judgments.py - Load judgment PDFs into Qdrant.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from pipeline.ingest import load_documents, extract_text_from_pdf
from pipeline.embeddings import EmbeddingService


def main():
    print("=" * 60)
    print("LEGAL LENS - Load Judgment PDFs")
    print("=" * 60)
    
    # Get Qdrant Cloud credentials
    cloud_url = os.getenv("QDRANT_CLOUD_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    
    print("\n[1/3] Connecting to Qdrant Cloud...")
    embedding_service = EmbeddingService(
        cloud_url=cloud_url,
        api_key=api_key,
        model_name="BAAI/bge-m3"
    )
    print("[OK] Connected!")
    
    print("\n[2/3] Loading judgment PDFs...")
    
    # Check multiple possible locations for judgment PDFs
    possible_paths = [
        Path(__file__).parent.parent / "data" / "judgements",
        Path(__file__).parent.parent.parent / "data" / "judgements",
        Path("c:/Users/RachitGarg/OneDrive - SP JAIN SCHOOL OF GLOBAL MANAGEMENT/Desktop/tiwari/Designs/data/judgements"),
    ]
    
    judgments_dir = None
    for p in possible_paths:
        if p.exists():
            judgments_dir = p
            break
    
    if not judgments_dir:
        print("[ERROR] Judgments directory not found!")
        print("Searched:", [str(p) for p in possible_paths])
        return
    
    print(f"[OK] Found judgments at: {judgments_dir}")
    
    # Load PDFs
    documents = []
    pdf_files = list(judgments_dir.glob("*.pdf"))
    print(f"[OK] Found {len(pdf_files)} PDF files")
    
    for i, pdf_path in enumerate(pdf_files):
        print(f"    [{i+1}/{len(pdf_files)}] Processing {pdf_path.name}...")
        try:
            content = extract_text_from_pdf(str(pdf_path))
            # Truncate very long documents to first 10000 chars for embedding
            if len(content) > 10000:
                content = content[:10000] + "...[truncated]"
            
            documents.append({
                "id": pdf_path.stem,
                "filename": pdf_path.name,
                "content": content,
                "source_type": ".pdf"
            })
            print(f"        Extracted {len(content)} chars")
        except Exception as e:
            print(f"        [ERROR] Failed: {e}")
    
    if not documents:
        print("[ERROR] No documents loaded!")
        return
    
    print(f"\n[OK] Loaded {len(documents)} documents")
    
    print("\n[3/3] Generating embeddings and uploading...")
    embedding_service.embed_documents(documents)
    print(f"[OK] Uploaded {len(documents)} documents to Qdrant Cloud!")
    
    print("\n[TEST] Searching for 'medical negligence'...")
    results = embedding_service.search("medical negligence", top_k=3)
    for r in results:
        print(f"    Score: {r['score']:.4f} | {r['payload'].get('filename', 'N/A')}")
    
    print("\n" + "=" * 60)
    print("Judgment PDFs loaded successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
