"""Test LightRAG indexing and query."""
import asyncio
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

# Verify API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("ERROR: OPENAI_API_KEY not found in .env")
    exit(1)
print(f"API Key loaded: {api_key[:20]}...")

from core.lightrag_engine import LightRAGEngine

async def test():
    print("\n=== Initializing LightRAG ===")
    engine = LightRAGEngine()
    
    success = await engine.initialize()
    if not success:
        print("Failed to initialize LightRAG")
        return
    
    print("\n=== Indexing Documents ===")
    await engine.index_documents()
    
    print("\n=== Testing Query ===")
    result = await engine.query("What is medical negligence?")
    
    if result.get("error"):
        print(f"Query error: {result.get('answer')}")
    else:
        print(f"Answer:\n{result.get('answer', 'No answer')[:500]}")
    
    await engine.finalize()
    print("\n=== Done ===")

if __name__ == "__main__":
    asyncio.run(test())
