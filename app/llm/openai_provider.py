from langchain_openai import ChatOpenAI

from app.config import settings
from app.llm.base import BaseLLM


class OpenAIProvider(BaseLLM):

    def __init__(self):

        self.client = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=settings.TEMPERATURE
        )

    def invoke(self, prompt: str):

        return self.client.invoke(prompt)