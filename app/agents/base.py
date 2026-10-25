from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Dict
from typing import Optional

from app.state import WorkflowState


def record_agent_event(
    state: WorkflowState,
    agent: str,
    summary: str,
    status: str = "completed",
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Record a concise execution trace without exposing private reasoning."""
    trace = list(state.get("agent_trace", []))
    trace.append({
        "agent": agent,
        "status": status,
        "summary": summary,
        "metadata": metadata or {},
    })
    state["agent_trace"] = trace


def load_knowledge_context(
    state: WorkflowState,
    knowledge_tool,
    top_k: int,
    agent_name: str,
) -> None:
    """Load shared RAG evidence through the agent's granted Tool."""
    result = knowledge_tool.invoke({
        "query": state["question"],
        "top_k": top_k,
    })
    if not result["ok"]:
        state["retrieved_context"] = []
        state["context_sources"] = []
        state["tool_results"]["knowledge_search"] = {
            "ok": False,
            "source": result["source"],
            "error_code": result.get("error_code"),
        }
        record_agent_event(
            state,
            agent_name,
            "知识检索失败，继续使用无资料模式",
            status="degraded",
            metadata={"tool": knowledge_tool.name},
        )
        return

    documents = result["data"]["documents"]
    state["retrieved_context"] = documents
    state["context_sources"] = [
        document["id"] for document in documents
    ]
    state["tool_results"]["knowledge_search"] = {
        "ok": True,
        "source": result["source"],
        "document_count": len(documents),
        "as_of": result["as_of"],
    }


class BaseAgent(ABC):
    """Common contract implemented by every LangGraph agent node."""

    name = "BaseAgent"
    responsibility = "Unassigned"

    def __init__(self, llm=None):
        self.llm = llm

    @abstractmethod
    def execute(self, state: WorkflowState) -> WorkflowState:
        pass
