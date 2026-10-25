from langchain_anthropic import ChatAnthropic

from app.config import settings
from app.llm.base import BaseLLM


class AnthropicProvider(BaseLLM):

    def __init__(self):

        self.client = ChatAnthropic(
            model=settings.CLAUDE_MODEL,
            temperature=settings.TEMPERATURE
        )

    def invoke(self, prompt: str):

        return self.client.invoke(prompt)