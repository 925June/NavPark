from app.agents.base import BaseAgent
from app.agents.base import load_knowledge_context
from app.agents.base import record_agent_event
from app.prompts import build_pricing_prompt
from app.tools.knowledge import search_parking_knowledge


class PricingAgent(BaseAgent):
    name = "PricingAgent"
    responsibility = "Explain pricing from evidence without executing payments."
    TOP_K = 2

    def __init__(self, llm=None, knowledge_tool=None):
        super().__init__(llm)
        self.knowledge_tool = (
            knowledge_tool or search_parking_knowledge
        )

    def execute(self, state):
        load_knowledge_context(
            state,
            self.knowledge_tool,
            self.TOP_K,
            self.name,
        )
        context = "\n\n".join(
            document["content"]
            for document in state.get("retrieved_context", [])
        )

        prompt = build_pricing_prompt(
            state["question"],
            context,
            state.get("history", []),
        )

        response = self.llm.invoke(prompt)
        state["draft_response"] = response.content.strip()
        state["intent"] = "pricing"
        record_agent_event(
            state,
            self.name,
            "生成价格与计费草稿",
            metadata={
                "source_count": len(state.get("context_sources", [])),
                "tool": self.knowledge_tool.name,
            },
        )

        return state
