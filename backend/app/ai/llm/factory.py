from functools import lru_cache

from app.ai.llm.base import LLMProvider
from app.core.config import settings
from app.core.exceptions import AppError


@lru_cache
def get_llm_provider() -> LLMProvider:
    if settings.LLM_PROVIDER == "anthropic":
        from app.ai.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider()
    if settings.LLM_PROVIDER == "ollama":
        from app.ai.llm.ollama_provider import OllamaProvider

        return OllamaProvider()
    raise AppError(f"Unknown LLM provider: {settings.LLM_PROVIDER}")
