from app.config import settings

from app.llm.openai_provider import OpenAIProvider
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.local_provider import LocalProvider


class LLMFactory:

    @staticmethod
    def create():

        if settings.LLM_PROVIDER == "local":
            return LocalProvider()

        if settings.LLM_PROVIDER == "openai":
            return OpenAIProvider()

        if settings.LLM_PROVIDER == "anthropic":
            return AnthropicProvider()

        raise Exception(
            f"Provider {settings.LLM_PROVIDER} not supported."
        )
