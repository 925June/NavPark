from langchain_openai import ChatOpenAI

from app.config import settings
from app.llm.base import BaseLLM


class DeepSeekConfigurationError(RuntimeError):
    """Raised when DeepSeek is selected but no API key is configured."""


class DeepSeekProvider(BaseLLM):
    """DeepSeek chat provider through the OpenAI-compatible API."""

    def __init__(self):
        self.model_name = settings.DEEPSEEK_MODEL
        self.client = None

        if settings.DEEPSEEK_API_KEY:
            self.client = ChatOpenAI(
                model=settings.DEEPSEEK_MODEL,
                temperature=settings.TEMPERATURE,
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL,
                timeout=settings.DEEPSEEK_TIMEOUT,
            )

    @property
    def is_configured(self) -> bool:
        return self.client is not None

    def invoke(self, prompt: str):
        if self.client is None:
            raise DeepSeekConfigurationError(
                "DEEPSEEK_API_KEY is not configured. "
                "Add it to the .env file and restart the server."
            )

        return self.client.invoke(prompt)
