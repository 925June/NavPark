from typing import List
from app.rag.base import BaseRetriever
from app.rag.embeddings import EmbeddingsProvider
from app.rag.documents import DocumentStore
from app.config import settings


class ChromaRetriever(BaseRetriever):
    """ChromaDB-based retriever for production use."""

    def __init__(self):
        try:
            import chromadb
            self.client = chromadb.Client()
            self.collection_name = settings.CHROMA_COLLECTION
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name
            )
            self.embeddings = EmbeddingsProvider()
            self._initialize_collection()
        except ImportError:
            print("ChromaDB not installed, falling back to simple retriever")
            self._fallback = SimpleRetriever()

    def _initialize_collection(self):
        """Initialize collection with documents if empty."""
        if self.collection.count() == 0:
            doc_store = DocumentStore(settings.DOCUMENTS_DIR)
            documents = doc_store.get_all_documents()
            
            if documents:
                ids = []
                texts = []
                metadatas = []
                
                for doc in documents:
                    ids.append(doc["id"])
                    texts.append(doc["content"])
                    metadatas.append(doc.get("metadata", {}))
                
                embeddings = [
                    self.embeddings.embed_text(text) 
                    for text in texts
                ]
                
                self.collection.add(
                    ids=ids,
                    documents=texts,
                    embeddings=embeddings,
                    metadatas=metadatas
                )

    def retrieve(self, query: str, top_k: int = 3) -> List[str]:
        """Retrieve relevant documents using ChromaDB."""
        if hasattr(self, '_fallback'):
            return self._fallback.retrieve(query, top_k)
        
        query_embedding = self.embeddings.embed_text(query)
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        
        return results.get("documents", [[]])[0]


class SimpleRetriever(BaseRetriever):
    """Simple keyword-based retriever for local development."""

    def __init__(self):
        self.doc_store = DocumentStore(settings.DOCUMENTS_DIR)

    def retrieve(self, query: str, top_k: int = 3) -> List[str]:
        """Retrieve relevant documents using keyword search."""
        return self.doc_store.search_by_keyword(query, top_k)


def get_retriever() -> BaseRetriever:
    """Factory function to get the appropriate retriever."""
    if not settings.ENABLE_RAG:
        return DisabledRetriever()
    
    try:
        return ChromaRetriever()
    except Exception:
        return SimpleRetriever()


class DisabledRetriever(BaseRetriever):
    """Retriever that returns no documents when RAG is disabled."""

    def retrieve(self, query: str, top_k: int = 3) -> List[str]:
        return []
