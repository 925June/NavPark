from typing import List
from app.rag.base import BaseEmbeddings
from app.llm.factory import LLMFactory


class EmbeddingsProvider(BaseEmbeddings):

    def __init__(self):
        self.llm = LLMFactory.create()

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding using the configured LLM provider.
        
        For local provider, returns a simple hash-based embedding.
        For OpenAI/Anthropic, would use their embedding APIs.
        """
        provider_name = type(self.llm).__name__
        
        if "Local" in provider_name:
            # Simple hash-based embedding for local provider
            return self._simple_embedding(text)
        else:
            # Would call actual embedding API for OpenAI/Anthropic
            # For now, fall back to simple embedding
            return self._simple_embedding(text)

    def _simple_embedding(self, text: str) -> List[float]:
        """Generate a simple hash-based embedding for local testing."""
        import hashlib
        
        # Create a deterministic 384-dimensional embedding
        hash_obj = hashlib.sha256(text.encode())
        hash_hex = hash_obj.hexdigest()
        
        # Convert hex to float values
        embedding = []
        for i in range(0, len(hash_hex), 2):
            byte_val = int(hash_hex[i:i+2], 16)
            normalized = byte_val / 255.0
            embedding.append(normalized)
        
        # Pad or truncate to 384 dimensions (common embedding size)
        while len(embedding) < 384:
            embedding.append(0.0)
        
        return embedding[:384]
