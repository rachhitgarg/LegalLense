"""
build_index.py - Build FAISS index from judgment documents.

Run this script locally whenever you add new judgment files to the data/judgments folder.
It will:
1. Read all PDFs from data/judgments/
2. Extract text using pdfminer
3. Generate embeddings using sentence-transformers
4. Build and save FAISS index

Usage:
    python build_index.py

The generated index files will be committed to the repo and used by the server.
"""

import json
import os
import sys
import pickle
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from a PDF file."""
    try:
        from pdfminer.high_level import extract_text
        text = extract_text(str(pdf_path))
        return text.strip()
    except Exception as e:
        print(f"  [ERROR] Could not extract text from {pdf_path.name}: {e}")
        return ""


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks for better search."""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind('.')
            if last_period > chunk_size // 2:
                end = start + last_period + 1
                chunk = text[start:end]
        
        if chunk.strip():
            chunks.append(chunk.strip())
        
        start = end - overlap
    
    return chunks


def load_existing_documents() -> List[Dict]:
    """Load existing sample documents."""
    # Sample landmark cases (always included)
    return [
        {
            "doc_id": "jacob_mathew_2005",
            "title": "Jacob Mathew vs State of Punjab (2005)",
            "content": """This landmark case established the comprehensive law on medical negligence in India. 
The Supreme Court held that a medical professional can only be held liable for negligence if it is established that:
1. He did not possess the requisite skill which he professed to have
2. He did not exercise reasonable care in its exercise

The court laid down specific guidelines for prosecuting medical professionals, including:
- Private complaints cannot be entertained unless a prima facie case of negligence exists
- Simple lack of care, error of judgment, or accident is not negligence
- The doctor must be shown to have acted with gross negligence or recklessness""",
            "keywords": ["medical negligence", "doctor liability", "malpractice", "prosecution"],
            "statutes": ["IPC 304A", "BNS 106"],
            "year": 2005,
            "court": "Supreme Court of India",
            "source": "sample"
        },
        {
            "doc_id": "kesavananda_bharati_1973",
            "title": "Kesavananda Bharati vs State of Kerala (1973)",
            "content": """The most important constitutional law case in India. The Supreme Court established the Basic Structure Doctrine.
Key holdings: Parliament has the power to amend any part of the Constitution, but cannot amend the basic structure.
Basic structure includes: fundamental rights, secularism, federalism, separation of powers, judicial review, democracy.""",
            "keywords": ["basic structure", "constitution", "amendment", "parliament power"],
            "statutes": ["Article 368", "Article 13"],
            "year": 1973,
            "court": "Supreme Court of India",
            "source": "sample"
        },
        {
            "doc_id": "navtej_johar_2018",
            "title": "Navtej Singh Johar vs Union of India (2018)",
            "content": """The Supreme Court decriminalized homosexuality by reading down Section 377 of the Indian Penal Code.
Key holdings: Consensual sexual conduct between adults of the same sex in private is not a crime.
Section 377 is unconstitutional to the extent it criminalizes consensual homosexual acts.
The right to sexual orientation and gender identity is protected under Article 21.""",
            "keywords": ["section 377", "homosexuality", "LGBTQ", "decriminalization", "privacy"],
            "statutes": ["IPC 377", "Article 14", "Article 21"],
            "year": 2018,
            "court": "Supreme Court of India",
            "source": "sample"
        },
        {
            "doc_id": "puttaswamy_2017",
            "title": "K.S. Puttaswamy vs Union of India (2017)",
            "content": """The landmark Right to Privacy judgment. A nine-judge Constitution Bench unanimously held that right to privacy is a fundamental right.
Privacy is intrinsic to Article 21 (right to life and personal liberty).
Privacy includes: bodily autonomy, personal identity, informational privacy, decisional privacy.
This judgment is foundational for data protection law in India.""",
            "keywords": ["privacy", "fundamental right", "article 21", "data protection"],
            "statutes": ["Article 21", "Article 14", "Article 19"],
            "year": 2017,
            "court": "Supreme Court of India",
            "source": "sample"
        },
        {
            "doc_id": "vishaka_1997",
            "title": "Vishaka vs State of Rajasthan (1997)",
            "content": """Landmark case that laid down guidelines for prevention of sexual harassment at workplace.
Sexual harassment at workplace violates fundamental rights under Articles 14, 19(1)(g), and 21.
The court laid down binding guidelines known as 'Vishaka Guidelines'.
These guidelines have the force of law until proper legislation is enacted.""",
            "keywords": ["sexual harassment", "workplace", "vishaka guidelines", "women's rights"],
            "statutes": ["Article 14", "Article 19", "Article 21", "POSH Act 2013"],
            "year": 1997,
            "court": "Supreme Court of India",
            "source": "sample"
        }
    ]


def process_pdf_folder(folder_path: Path) -> List[Dict]:
    """Process all PDFs in a folder and return document chunks."""
    documents = []
    
    if not folder_path.exists():
        print(f"Creating judgments folder: {folder_path}")
        folder_path.mkdir(parents=True, exist_ok=True)
        return documents
    
    pdf_files = list(folder_path.glob("*.pdf"))
    print(f"\nFound {len(pdf_files)} PDF files in {folder_path}")
    
    for pdf_path in pdf_files:
        print(f"\nProcessing: {pdf_path.name}")
        
        # Extract text
        text = extract_text_from_pdf(pdf_path)
        
        if not text:
            print(f"  [SKIP] No text extracted")
            continue
        
        print(f"  Extracted {len(text)} characters")
        
        # Create document entry
        doc_id = pdf_path.stem.lower().replace(" ", "_").replace("-", "_")
        
        # Extract title from first line or use filename
        first_line = text.split('\n')[0].strip()
        title = first_line if len(first_line) < 200 else pdf_path.stem
        
        # Create chunks for long documents
        if len(text) > 2000:
            chunks = chunk_text(text, chunk_size=1500, overlap=200)
            print(f"  Created {len(chunks)} chunks")
            
            for i, chunk in enumerate(chunks):
                documents.append({
                    "doc_id": f"{doc_id}_chunk_{i+1}",
                    "title": f"{title} (Part {i+1})",
                    "content": chunk,
                    "keywords": [],  # Could use NLP to extract keywords
                    "statutes": [],  # Could use regex to extract statute refs
                    "source": "pdf",
                    "filename": pdf_path.name
                })
        else:
            documents.append({
                "doc_id": doc_id,
                "title": title,
                "content": text[:3000],  # Limit content size
                "keywords": [],
                "statutes": [],
                "source": "pdf",
                "filename": pdf_path.name
            })
        
        print(f"  Added to index")
    
    return documents


def build_faiss_index(documents: List[Dict], output_dir: Path) -> bool:
    """Build FAISS index from documents."""
    try:
        from sentence_transformers import SentenceTransformer
        import faiss
    except ImportError:
        print("\n[ERROR] Required packages not installed. Run:")
        print("  pip install sentence-transformers faiss-cpu")
        return False
    
    print(f"\n{'='*60}")
    print("Building FAISS Index")
    print(f"{'='*60}")
    
    # Load model
    print("\nLoading embedding model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print("  Model loaded!")
    
    # Generate embeddings
    print(f"\nGenerating embeddings for {len(documents)} documents...")
    texts = [f"{doc['title']} {doc['content']}" for doc in documents]
    embeddings = model.encode(texts, show_progress_bar=True)
    print(f"  Generated {embeddings.shape[0]} embeddings of dimension {embeddings.shape[1]}")
    
    # Normalize for cosine similarity
    faiss.normalize_L2(embeddings)
    
    # Create FAISS index
    print("\nBuilding FAISS index...")
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)  # Inner product = cosine sim for normalized vectors
    index.add(embeddings)
    print(f"  Index contains {index.ntotal} vectors")
    
    # Save everything
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save documents
    docs_file = output_dir / "documents.json"
    with open(docs_file, "w", encoding="utf-8") as f:
        json.dump(documents, f, indent=2, ensure_ascii=False)
    print(f"\nSaved documents to: {docs_file}")
    
    # Save FAISS index
    index_file = output_dir / "faiss.index"
    faiss.write_index(index, str(index_file))
    print(f"Saved FAISS index to: {index_file}")
    
    # Save embeddings as numpy array (backup)
    embeddings_file = output_dir / "embeddings.npy"
    np.save(embeddings_file, embeddings)
    print(f"Saved embeddings to: {embeddings_file}")
    
    # Save metadata
    metadata = {
        "created_at": datetime.now().isoformat(),
        "num_documents": len(documents),
        "embedding_model": "all-MiniLM-L6-v2",
        "embedding_dimension": dimension,
        "index_type": "IndexFlatIP"
    }
    metadata_file = output_dir / "index_metadata.json"
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved metadata to: {metadata_file}")
    
    return True


def main():
    print("="*60)
    print("Legal Lens - FAISS Index Builder")
    print("="*60)
    
    # Paths
    script_dir = Path(__file__).parent
    data_dir = script_dir / "data"
    judgments_dir = data_dir / "judgments"
    
    # Load sample documents
    print("\nLoading sample landmark cases...")
    documents = load_existing_documents()
    print(f"  Loaded {len(documents)} sample cases")
    
    # Process PDFs from judgments folder
    pdf_documents = process_pdf_folder(judgments_dir)
    documents.extend(pdf_documents)
    
    print(f"\n{'='*60}")
    print(f"Total documents to index: {len(documents)}")
    print(f"{'='*60}")
    
    # Build FAISS index
    success = build_faiss_index(documents, data_dir)
    
    if success:
        print("\n" + "="*60)
        print("SUCCESS! Index built and saved.")
        print("="*60)
        print("\nNext steps:")
        print("1. Commit the generated files:")
        print("   git add backend/data/")
        print("   git commit -m 'Update FAISS index'")
        print("   git push")
        print("\n2. The server will use the pre-built index automatically.")
        print("\nTo add more documents:")
        print(f"  1. Add PDF files to: {judgments_dir}")
        print("  2. Run this script again: python build_index.py")
        print("  3. Commit and push the changes")
    else:
        print("\n[FAILED] Could not build index. See errors above.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
