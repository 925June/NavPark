from app.agents.base import BaseAgent


class JudgeAgent(BaseAgent):

    def execute(self, state):

        prompt = f"""
Evaluate this answer.

Question:

{state["question"]}

Answer:

{state["response"]}

Should a human review it?

Answer ONLY

YES

or

NO
"""

        result = self.llm.invoke(prompt)

        state["requires_human"] = (
            result.content.strip().upper() == "YES"
        )

        return state