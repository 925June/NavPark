from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import TypedDict


class WorkflowState(TypedDict):

    #################################################
    # Incoming Request
    #################################################

    question: str

    user_id: Optional[str]

    session_id: str

    history: List[Dict[str, str]]

    location: Optional[Dict[str, float]]

    #################################################
    # Orchestration
    #################################################

    route_reason: str

    workflow_plan: List[str]

    agent_trace: List[Dict[str, Any]]

    #################################################
    # Supervisor
    #################################################

    next_agent: Optional[str]

    #################################################
    # Customer
    #################################################

    customer_id: Optional[str]

    #################################################
    # Parking Information
    #################################################

    parking_lot_id: Optional[str]

    reservation_id: Optional[str]

    vehicle_plate: Optional[str]

    #################################################
    # AI Decisions
    #################################################

    intent: Optional[str]

    confidence: float

    #################################################
    # External APIs
    #################################################

    api_result: dict

    tool_results: Dict[str, Any]

    #################################################
    # Knowledge Retrieval
    #################################################

    retrieved_context: List[Dict[str, str]]

    context_sources: List[str]

    #################################################
    # Draft and Audit
    #################################################

    draft_response: Optional[str]

    audit_result: Dict[str, Any]

    human_review_reason: Optional[str]

    human_review_status: Optional[str]

    #################################################
    # Human Review
    #################################################

    requires_human: bool

    #################################################
    # Final Answer
    #################################################

    response: Optional[str]

    guardrail_failures: List[str]


def create_workflow_state(
    question: str,
    user_id: Optional[str] = None,
    session_id: str = "",
    history: Optional[List[Dict[str, str]]] = None,
    location: Optional[Dict[str, float]] = None,
) -> WorkflowState:
    """Build a complete initial state for LangGraph."""
    return {
        "question": question,
        "user_id": user_id,
        "session_id": session_id,
        "history": list(history or []),
        "location": location,
        "route_reason": "",
        "workflow_plan": [],
        "agent_trace": [],
        "next_agent": None,
        "customer_id": None,
        "parking_lot_id": None,
        "reservation_id": None,
        "vehicle_plate": None,
        "intent": None,
        "confidence": 1.0,
        "api_result": {},
        "tool_results": {},
        "retrieved_context": [],
        "context_sources": [],
        "draft_response": None,
        "audit_result": {},
        "human_review_reason": None,
        "human_review_status": None,
        "requires_human": False,
        "response": None,
        "guardrail_failures": [],
    }
