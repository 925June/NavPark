from app.agents.base import BaseAgent
from app.rag import get_retriever


class SupportAgent(BaseAgent):

    def __init__(self, llm):
        super().__init__(llm)
        self.retriever = get_retriever()

    def execute(self, state):

        # Retrieve relevant support/policy documents
        context_docs = self.retriever.retrieve(
            state["question"],
            top_k=3
        )

        context = "\n\n".join(context_docs) if context_docs else ""

        prompt = f"""
You are a parking support assistant. Answer the customer's question using the provided context.

Context:
{context}

Question:
{state["question"]}

Provide helpful, accurate information about parking policies, facilities, and general support.
"""

        response = self.llm.invoke(prompt)
        state["response"] = response.content.strip()

        return state