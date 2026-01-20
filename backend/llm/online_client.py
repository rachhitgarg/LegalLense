"""
online_client.py - OpenAI API wrapper for Legal Lens.

Uses the OpenAI API for the prototype. Later, swap to local_stub.py for
offline Llama 3.x inference.
"""

import os
from typing import Optional, Generator
from openai import OpenAI


class OnlineLLMClient:
    """Wrapper for OpenAI API calls."""
    
    SYSTEM_PROMPT = """You are a legal research assistant for Indian law. Your role is to:
1. Answer questions about Indian legal precedents, statutes, and procedures.
2. Provide accurate citations from the context provided.
3. Explain legal concepts in simple terms.
4. Map old statutes (IPC, CrPC) to new ones (BNS, BNSS) when relevant.

IMPORTANT RULES:
- Only use information from the provided context.
- Always cite paragraph numbers and case names.
- Never predict case outcomes or give legal advice.
- Clearly state when information is not available in the context.
- This is an educational tool, not legal advice.
"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o-mini"
    
    def generate(
        self,
        query: str,
        context: str,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> str:
        """Generate a response for the given query with context."""
        user_message = f"""Context:
{context}

User Query: {query}

Provide a well-structured answer with citations from the context."""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        return response.choices[0].message.content
    
    def stream_generate(
        self,
        query: str,
        context: str,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> Generator[str, None, None]:
        """Stream a response for the given query with context."""
        user_message = f"""Context:
{context}

User Query: {query}

Provide a well-structured answer with citations from the context."""
        
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


if __name__ == "__main__":
    client = OnlineLLMClient()
    print("Online LLM client initialized.")
    print(f"Using model: {client.model}")
