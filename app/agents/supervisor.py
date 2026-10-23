from app.agents.base import BaseAgent


class SupervisorAgent(BaseAgent):

    def execute(self, state):

        history = "\n".join(
            f'{message["role"]}: {message["content"]}'
            for message in state.get("history", [])[-6:]
        )

        prompt = f"""
You are a supervisor.

Choose ONE agent.

Available:

reservation

pricing

support

judge

Conversation history:

{history}

Question:

{state["question"]}

Only answer with the agent name.
"""

        response = self.llm.invoke(prompt)

        state["next_agent"] = response.content.strip().lower()

        return state
