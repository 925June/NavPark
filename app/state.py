from typing import TypedDict
from typing import Optional
from typing import List
from typing import Dict


class WorkflowState(TypedDict):

    #################################################
    # Incoming Request
    #################################################

    question: str

    session_id: str

    history: List[Dict[str, str]]

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

    #################################################
    # Human Review
    #################################################

    requires_human: bool

    #################################################
    # Final Answer
    #################################################

    response: Optional[str]
