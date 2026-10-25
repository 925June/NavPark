from typing import Dict
from typing import List

from app.tools.billing import calculate_parking_fee
from app.tools.knowledge import search_parking_knowledge
from app.tools.parking import get_parking_availability
from app.tools.parking import plan_parking_route
from app.tools.reservation import validate_reservation_request


TOOL_BINDINGS = {
    "SupervisorAgent": (),
    "ParkingAgent": (
        get_parking_availability,
        plan_parking_route,
    ),
    "ReservationAgent": (
        search_parking_knowledge,
        validate_reservation_request,
    ),
    "PricingAgent": (
        search_parking_knowledge,
        calculate_parking_fee,
    ),
    "SupportAgent": (
        search_parking_knowledge,
    ),
    "JudgeAgent": (),
    "ResponseAgent": (),
}


def get_tools_for_agent(agent_name: str) -> List:
    """Return only the tools explicitly granted to an Agent."""
    return list(TOOL_BINDINGS.get(agent_name, ()))


def get_tool_bindings() -> Dict[str, List[str]]:
    return {
        agent: [tool.name for tool in tools]
        for agent, tools in TOOL_BINDINGS.items()
    }
