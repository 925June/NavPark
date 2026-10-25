from app.agents.base import BaseAgent
from app.agents.base import load_knowledge_context
from app.agents.base import record_agent_event
from app.prompts import build_support_prompt
from app.tools.knowledge import search_parking_knowledge


class SupportAgent(BaseAgent):
    name = "SupportAgent"
    responsibility = "Answer service and support questions from evidence."
    TOP_K = 3

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

        prompt = build_support_prompt(
            state["question"],
            context,
            state.get("history", []),
        )

        response = self.llm.invoke(prompt)
        state["draft_response"] = response.content.strip()
        state["intent"] = "support"
        record_agent_event(
            state,
            self.name,
            "生成服务支持草稿",
            metadata={
                "source_count": len(state.get("context_sources", [])),
                "tool": self.knowledge_tool.name,
            },
        )

        return state
