from langgraph.graph import END
from langgraph.graph import StateGraph

from app.agents.judge import JudgeAgent
from app.agents.parking import ParkingAgent
from app.agents.pricing import PricingAgent
from app.agents.reservation import ReservationAgent
from app.agents.response import ResponseAgent
from app.agents.supervisor import SupervisorAgent
from app.agents.support import SupportAgent
from app.graph.router import supervisor_router
from app.llm.factory import LLMFactory
from app.state import WorkflowState


llm = LLMFactory.create()

supervisor = SupervisorAgent(llm)
parking = ParkingAgent(llm)
reservation = ReservationAgent(llm)
pricing = PricingAgent(llm)
support = SupportAgent(llm)
judge = JudgeAgent(llm)
response = ResponseAgent(llm)


builder = StateGraph(WorkflowState)

builder.add_node("supervisor", supervisor.execute)
builder.add_node("parking", parking.execute)
builder.add_node("reservation", reservation.execute)
builder.add_node("pricing", pricing.execute)
builder.add_node("support", support.execute)
builder.add_node("judge", judge.execute)
builder.add_node("response", response.execute)

builder.set_entry_point("supervisor")

builder.add_conditional_edges(
    "supervisor",
    supervisor_router,
    {
        "parking": "parking",
        "reservation": "reservation",
        "pricing": "pricing",
        "support": "support",
    },
)

builder.add_edge("parking", "judge")
builder.add_edge("reservation", "judge")
builder.add_edge("pricing", "judge")
builder.add_edge("support", "judge")
builder.add_edge("judge", "response")
builder.add_edge("response", END)

graph = builder.compile()
