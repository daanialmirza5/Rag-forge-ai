"""LLM provider abstraction.

Every generation call in the app (RAG answer synthesis, query rewriting,
future features) goes through this interface rather than calling the
Anthropic SDK directly, so the provider can be swapped via configuration —
see `app/ai/llm/factory.py`.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from typing import Literal

Role = Literal["user", "assistant"]
Effort = Literal["low", "medium", "high", "xhigh", "max"]


@dataclass(frozen=True, slots=True)
class LLMMessage:
    role: Role
    content: str


@dataclass(frozen=True, slots=True)
class LLMUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


@dataclass(frozen=True, slots=True)
class LLMResponse:
    content: str
    model: str
    stop_reason: str | None
    usage: LLMUsage = field(default_factory=LLMUsage)


class LLMStream(ABC):
    """Handle returned by `LLMProvider.stream(...)`. Consume `text_stream` for
    incremental output, then call `get_final_response()` once the stream is
    exhausted to get the full text + usage."""

    @property
    @abstractmethod
    def text_stream(self) -> AsyncIterator[str]: ...

    @abstractmethod
    async def get_final_response(self) -> LLMResponse: ...


class LLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
        effort: Effort | None = None,
        enable_thinking: bool | None = None,
    ) -> LLMResponse:
        """Non-streaming generation — use for short, latency-tolerant calls
        (e.g. query rewriting). Prefer `stream()` for anything user-facing.

        `effort`/`enable_thinking` override the configured defaults
        (`LLM_EFFORT`/`LLM_ENABLE_THINKING`) for this call only — e.g. query
        rewriting wants `effort="low", enable_thinking=False` since it's a
        cheap, latency-sensitive task that doesn't benefit from either."""
        ...

    @abstractmethod
    def stream(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> AbstractAsyncContextManager[LLMStream]:
        """Usage: `async with provider.stream(...) as s: async for chunk in
        s.text_stream: ...`"""
        ...
