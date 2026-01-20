"""
local_stub.py - Placeholder for local Llama 3.x inference.

This module will later be implemented to load and run a local Llama 3.x model
using vLLM, llama.cpp, or similar inference engines.

For now, it mirrors the OnlineLLMClient interface but raises NotImplementedError.
"""

from typing import Generator


class LocalLLMClient:
    """Placeholder for local Llama 3.x inference."""
    
    SYSTEM_PROMPT = """You are a legal research assistant for Indian law..."""  # Same as online
    
    def __init__(self, model_path: str = None):
        """
        Initialize the local LLM client.
        
        Args:
            model_path: Path to the local model weights (GGUF format recommended).
        """
        self.model_path = model_path
        self.model = None
        # TODO: Load model using llama.cpp or vLLM
    
    def load_model(self):
        """Load the local model into memory."""
        raise NotImplementedError(
            "Local LLM not yet implemented. Use OnlineLLMClient for now."
        )
    
    def generate(
        self,
        query: str,
        context: str,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> str:
        """Generate a response using the local model."""
        raise NotImplementedError(
            "Local LLM not yet implemented. Use OnlineLLMClient for now."
        )
    
    def stream_generate(
        self,
        query: str,
        context: str,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> Generator[str, None, None]:
        """Stream a response using the local model."""
        raise NotImplementedError(
            "Local LLM not yet implemented. Use OnlineLLMClient for now."
        )


# Future implementation notes:
# 1. Use llama-cpp-python for CPU inference with GGUF models
# 2. Model recommendation: Llama-3-8B-Instruct-GGUF (Q4_K_M quantization)
# 3. Expected RAM usage: ~8GB for Q4_K_M on 8B model
# 4. For better quality, use Llama-3.1-8B-Instruct if hardware permits
