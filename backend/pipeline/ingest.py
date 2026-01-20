"""
ingest.py - Document ingestion module.

Reads PDFs and text files from the data/ folder, extracts text, and stores
processed documents for embedding generation.
"""

import os
from pathlib import Path
from pdfminer.high_level import extract_text


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text content from a PDF file."""
    return extract_text(pdf_path)


def load_documents(data_dir: str = "data") -> list[dict]:
    """
    Load all documents from the data directory.
    
    Returns a list of dicts with keys: id, filename, content, source_type
    """
    documents = []
    data_path = Path(data_dir)
    
    if not data_path.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")
    
    for file_path in data_path.glob("**/*"):
        if file_path.is_file():
            doc = {
                "id": file_path.stem,
                "filename": file_path.name,
                "source_type": file_path.suffix.lower(),
            }
            
            if file_path.suffix.lower() == ".pdf":
                doc["content"] = extract_text_from_pdf(str(file_path))
            elif file_path.suffix.lower() in [".txt", ".md"]:
                doc["content"] = file_path.read_text(encoding="utf-8")
            elif file_path.suffix.lower() == ".json":
                doc["content"] = file_path.read_text(encoding="utf-8")
            else:
                continue  # Skip unsupported file types
            
            documents.append(doc)
    
    return documents


if __name__ == "__main__":
    docs = load_documents()
    print(f"Loaded {len(docs)} documents.")
    for doc in docs[:3]:
        print(f"  - {doc['filename']}: {len(doc['content'])} chars")
