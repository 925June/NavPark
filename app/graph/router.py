from app.state import WorkflowState


def supervisor_router(state: WorkflowState):

    next_agent = state["next_agent"]

    if next_agent in {
        "reservation",
        "pricing",
        "support",
        "parking",
    }:
        return next_agent

    return "support"
