"""
build_openai_index.py - Build embeddings index using OpenAI API.

Run this script locally to generate document embeddings using OpenAI's API.
The embeddings are then committed to the repo and used by the server.

Usage:
    # Set your API key
    export OPENAI_API_KEY=your_key_here
    
    # Run the script
    python build_openai_index.py

This creates openai_embeddings.npy which the server loads for semantic search.
"""

import json
import os
import sys
import time
import numpy as np
from pathlib import Path
from typing import List

# OpenAI API settings
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536


def get_embedding(text: str, api_key: str) -> np.ndarray:
    """Get embedding from OpenAI API."""
    import requests
    
    response = requests.post(
        "https://api.openai.com/v1/embeddings",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": EMBEDDING_MODEL,
            "input": text
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        return np.array(data["data"][0]["embedding"])
    else:
        raise Exception(f"API error {response.status_code}: {response.text}")


def load_documents(data_dir: Path) -> List[dict]:
    """Load documents from JSON file."""
    docs_file = data_dir / "documents.json"
    
    if docs_file.exists():
        with open(docs_file, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        # Create sample documents
        return create_sample_documents(data_dir)


def create_sample_documents(data_dir: Path) -> List[dict]:
    """Create sample legal documents."""
    documents = [
        {
            "doc_id": "jacob_mathew_2005",
            "title": "Jacob Mathew vs State of Punjab (2005)",
            "content": "This landmark case established the comprehensive law on medical negligence in India. The Supreme Court held that a medical professional can only be held liable for negligence if it is established that he did not possess the requisite skill or did not exercise reasonable care. The court laid down specific guidelines for prosecuting medical professionals including that private complaints cannot be entertained unless a prima facie case of negligence exists. Simple lack of care, error of judgment, or accident is not negligence.",
            "keywords": ["medical negligence", "doctor liability", "malpractice", "prosecution"],
            "statutes": ["IPC 304A", "BNS 106"],
            "year": 2005,
            "court": "Supreme Court of India"
        },
        {
            "doc_id": "puttaswamy_2017",
            "title": "K.S. Puttaswamy vs Union of India (2017)",
            "content": "The landmark Right to Privacy judgment. A nine-judge Constitution Bench unanimously held that right to privacy is a fundamental right intrinsic to Article 21 (right to life and personal liberty). Privacy includes bodily autonomy, personal identity, informational privacy, and decisional privacy. This is foundational for data protection law in India. The court overruled MP Sharma (1954) and Kharak Singh (1962).",
            "keywords": ["privacy", "fundamental right", "article 21", "data protection", "aadhaar"],
            "statutes": ["Article 21", "Article 14", "Article 19"],
            "year": 2017,
            "court": "Supreme Court of India"
        },
        {
            "doc_id": "navtej_johar_2018",
            "title": "Navtej Singh Johar vs Union of India (2018)",
            "content": "The Supreme Court decriminalized homosexuality by reading down Section 377 of the Indian Penal Code. Consensual sexual conduct between adults of the same sex in private is not a crime. Section 377 is unconstitutional to the extent it criminalizes consensual homosexual acts. LGBTQ individuals have equal rights to privacy and dignity under Articles 14 and 21.",
            "keywords": ["section 377", "homosexuality", "LGBTQ", "decriminalization", "privacy"],
            "statutes": ["IPC 377", "Article 14", "Article 21"],
            "year": 2018,
            "court": "Supreme Court of India"
        },
        {
            "doc_id": "kesavananda_bharati_1973",
            "title": "Kesavananda Bharati vs State of Kerala (1973)",
            "content": "The most important constitutional law case establishing the Basic Structure Doctrine. The Supreme Court held that Parliament has power to amend the Constitution but cannot destroy its basic structure. Basic structure includes fundamental rights, secularism, federalism, separation of powers, judicial review, democracy, and rule of law.",
            "keywords": ["basic structure", "constitution", "amendment", "fundamental rights", "parliament"],
            "statutes": ["Article 368", "Article 13"],
            "year": 1973,
            "court": "Supreme Court of India"
        },
        {
            "doc_id": "vishaka_1997",
            "title": "Vishaka vs State of Rajasthan (1997)",
            "content": "Landmark case laying down Vishaka Guidelines for prevention of sexual harassment at workplace. Sexual harassment violates fundamental rights under Articles 14, 19(1)(g), and 21. The court filled legislative vacuum by laying down binding guidelines which were later codified as the Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013 (POSH Act).",
            "keywords": ["sexual harassment", "workplace", "vishaka guidelines", "women rights", "POSH"],
            "statutes": ["Article 14", "Article 19", "Article 21", "POSH Act 2013"],
            "year": 1997,
            "court": "Supreme Court of India"
        }
    ]
    
    data_dir.mkdir(parents=True, exist_ok=True)
    with open(data_dir / "documents.json", "w", encoding="utf-8") as f:
        json.dump(documents, f, indent=2, ensure_ascii=False)
    
    print(f"Created sample documents at {data_dir / 'documents.json'}")
    return documents


def main():
    print("=" * 60)
    print("Legal Lens - OpenAI Embeddings Index Builder")
    print("=" * 60)
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n[ERROR] OPENAI_API_KEY environment variable not set!")
        print("\nOn Windows:")
        print('  set OPENAI_API_KEY=your_key_here')
        print("\nOn Mac/Linux:")
        print('  export OPENAI_API_KEY=your_key_here')
        return 1
    
    # Paths
    script_dir = Path(__file__).parent
    data_dir = script_dir / "data"
    
    # Load documents
    print("\nLoading documents...")
    documents = load_documents(data_dir)
    print(f"  Loaded {len(documents)} documents")
    
    # Generate embeddings
    print(f"\nGenerating embeddings using {EMBEDDING_MODEL}...")
    embeddings = []
    
    for i, doc in enumerate(documents):
        # Combine title and content for embedding
        text = f"{doc['title']}\n{doc['content']}"
        
        print(f"  [{i+1}/{len(documents)}] {doc['doc_id']}...", end=" ")
        
        try:
            embedding = get_embedding(text, api_key)
            embeddings.append(embedding)
            print("OK")
        except Exception as e:
            print(f"ERROR: {e}")
            return 1
        
        # Rate limiting
        time.sleep(0.2)
    
    # Save embeddings
    embeddings_array = np.array(embeddings)
    output_file = data_dir / "openai_embeddings.npy"
    np.save(output_file, embeddings_array)
    
    print(f"\n{'=' * 60}")
    print("SUCCESS!")
    print(f"{'=' * 60}")
    print(f"\nSaved embeddings to: {output_file}")
    print(f"Shape: {embeddings_array.shape}")
    print(f"Model: {EMBEDDING_MODEL}")
    
    # Save metadata
    metadata = {
        "model": EMBEDDING_MODEL,
        "dimension": EMBEDDING_DIM,
        "num_documents": len(documents),
        "created_at": str(np.datetime64('now'))
    }
    with open(data_dir / "openai_index_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    print("\nNext steps:")
    print("  1. git add backend/data/")
    print("  2. git commit -m 'Update OpenAI embeddings'")
    print("  3. git push")
    print("\nMake sure OPENAI_API_KEY is set in Render environment!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
