from app.state import WorkflowState


def supervisor_router(state: WorkflowState):

    next_agent = state["next_agent"]

    if next_agent in {
        "reservation",
        "pricing",
        "support",
        "judge"
    }:
        return next_agent

    return "support"


def judge_router(state: WorkflowState):

    if state["requires_human"]:
        return "human"

    return "response"
