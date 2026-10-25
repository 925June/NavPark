from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from app.rag import get_retriever
from app.tools.base import tool_failure
from app.tools.base import tool_success


class KnowledgeSearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=3, ge=1, le=10)


def create_knowledge_search_tool(retriever=None):
    """Build a read-only knowledge tool with an injectable retriever."""
    active_retriever = retriever or get_retriever()

    @tool(
        "search_parking_knowledge",
        args_schema=KnowledgeSearchInput,
    )
    def search_parking_knowledge(query: str, top_k: int = 3) -> dict:
        """Search the approved parking knowledge base for evidence."""
        try:
            documents = active_retriever.retrieve(query, top_k=top_k)
            return tool_success(
                {
                    "documents": [
                        {
                            "id": f"doc-{index}",
                            "content": content,
                        }
                        for index, content in enumerate(
                            documents,
                            start=1,
                        )
                    ]
                },
                source="parking_knowledge_base",
                metadata={
                    "top_k": top_k,
                    "document_count": len(documents),
                },
            )
        except Exception as exc:
            return tool_failure(
                str(exc),
                source="parking_knowledge_base",
                error_code="knowledge_search_failed",
            )

    return search_parking_knowledge


search_parking_knowledge = create_knowledge_search_tool()
