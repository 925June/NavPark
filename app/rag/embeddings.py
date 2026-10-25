from typing import List
from app.rag.base import BaseEmbeddings


class EmbeddingsProvider(BaseEmbeddings):
    """Create deterministic local vectors for the lightweight RAG fallback."""

    def embed_text(self, text: str) -> List[float]:
        """Generate a hash-based embedding without another model provider."""
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
