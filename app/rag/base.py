from abc import ABC
from abc import abstractmethod
from typing import List


class BaseRetriever(ABC):

    @abstractmethod
    def retrieve(
        self,
        query: str,
        top_k: int = 3
    ) -> List[str]:
        """Retrieve relevant documents for a query."""
        pass


class BaseEmbeddings(ABC):

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a text."""
        pass
