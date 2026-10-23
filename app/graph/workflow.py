from langgraph.graph import StateGraph
from langgraph.graph import END

from app.state import WorkflowState

from app.llm.factory import LLMFactory

from app.agents.supervisor import SupervisorAgent
from app.agents.reservation import ReservationAgent
from app.agents.pricing import PricingAgent
from app.agents.support import SupportAgent
from app.agents.judge import JudgeAgent
from app.agents.response import ResponseAgent
from app.agents.human import HumanAgent

from app.graph.router import (
    supervisor_router,
    judge_router
)


llm = LLMFactory.create()


supervisor = SupervisorAgent(llm)
reservation = ReservationAgent(llm)
pricing = PricingAgent(llm)
support = SupportAgent(llm)
judge = JudgeAgent(llm)
response = ResponseAgent(llm)
human = HumanAgent(llm)


builder = StateGraph(WorkflowState)


builder.add_node(
    "supervisor",
    supervisor.execute
)

builder.add_node(
    "reservation",
    reservation.execute
)

builder.add_node(
    "pricing",
    pricing.execute
)

builder.add_node(
    "support",
    support.execute
)

builder.add_node(
    "judge",
    judge.execute
)

builder.add_node(
    "human",
    human.execute
)

builder.add_node(
    "response",
    response.execute
)


builder.set_entry_point(
    "supervisor"
)


builder.add_conditional_edges(
    "supervisor",
    supervisor_router,
    {
        "reservation": "reservation",
        "pricing": "pricing",
        "support": "support",
        "judge": "judge"
    }
)

builder.add_edge(
    "reservation",
    "judge"
)

builder.add_edge(
    "pricing",
    "judge"
)

builder.add_edge(
    "support",
    "judge"
)

builder.add_conditional_edges(
    "judge",
    judge_router,
    {
        "human": "human",
        "response": "response"
    }
)

builder.add_edge(
    "human",
    "response"
)

builder.add_edge(
    "response",
    END
)


graph = builder.compile()
