from app.agents.base import BaseAgent


class HumanAgent(BaseAgent):

    def execute(self, state):

        response = state.get("response") or ""

        state["response"] = response + (
            "\n\nApproved by Human."
        )

        return state
