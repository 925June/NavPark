from app.llm.deepseek_provider import DeepSeekProvider


class LLMFactory:
    """Create the single LLM provider used by every workflow agent."""

    @staticmethod
    def create() -> DeepSeekProvider:
        return DeepSeekProvider()
