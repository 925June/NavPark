from typing import List
from typing import Dict
from pathlib import Path


class DocumentStore:

    def __init__(self, documents_dir: str = "documents"):
        self.documents_dir = Path(documents_dir)
        self.documents: List[Dict[str, str]] = []
        self._load_documents()

    def _load_documents(self):
        """Load all text documents from the documents directory."""
        if not self.documents_dir.exists():
            self.documents_dir.mkdir(parents=True, exist_ok=True)
            return

        for file_path in self.documents_dir.glob("*.txt"):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.documents.append({
                    "id": file_path.stem,
                    "content": content,
                    "metadata": {
                        "source": str(file_path)
                    }
                })

    def add_document(
        self,
        doc_id: str,
        content: str,
        metadata: Dict = None
    ):
        """Add a document to the store."""
        if metadata is None:
            metadata = {}
        
        self.documents.append({
            "id": doc_id,
            "content": content,
            "metadata": metadata
        })

    def get_all_documents(self) -> List[Dict[str, str]]:
        """Return all documents."""
        return self.documents

    def search_by_keyword(
        self,
        query: str,
        top_k: int = 3
    ) -> List[str]:
        """Simple keyword-based search for local provider."""
        query_lower = query.lower()
        scored_docs = []

        for doc in self.documents:
            content_lower = doc["content"].lower()
            
            # Calculate simple relevance score
            score = 0
            query_words = query_lower.split()
            
            for word in query_words:
                if word in content_lower:
                    score += content_lower.count(word)
            
            if score > 0:
                scored_docs.append((score, doc["content"]))

        # Sort by score and return top_k
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc[1] for doc in scored_docs[:top_k]]
