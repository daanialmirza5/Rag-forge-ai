"""Anthropic Claude implementation of `LLMProvider`.

Uses adaptive thinking (configurable via `LLM_ENABLE_THINKING`/`LLM_EFFORT`)
and defaults to streaming for anything user-facing, per the model's
recommended usage pattern for long-output / latency-sensitive calls.

Note: this SDK version's typed `messages.create`/`messages.stream` signatures
expect the `anthropic.omit` sentinel (not the older `anthropic.NOT_GIVEN`) for
omitted optional parameters — see `anthropic._types.Omit`.
"""

from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager

import anthropic
from anthropic.types import MessageParam
from anthropic.types.output_config_param import OutputConfigParam
from anthropic.types.thinking_config_adaptive_param import ThinkingConfigAdaptiveParam
from anthropic.types.thinking_config_disabled_param import ThinkingConfigDisabledParam

from app.ai.llm.base import Effort, LLMMessage, LLMProvider, LLMResponse, LLMStream, LLMUsage
from app.core.config import settings
from app.core.exceptions import UpstreamProviderError
from app.core.logging import get_logger

logger = get_logger(__name__)

ThinkingConfig = ThinkingConfigAdaptiveParam | ThinkingConfigDisabledParam


def _thinking_config(enable_thinking: bool | None) -> ThinkingConfig:
    enabled = settings.LLM_ENABLE_THINKING if enable_thinking is None else enable_thinking
    if enabled:
        return ThinkingConfigAdaptiveParam(type="adaptive")
    return ThinkingConfigDisabledParam(type="disabled")


def _output_config(effort: Effort | None) -> OutputConfigParam:
    return OutputConfigParam(effort=effort or settings.LLM_EFFORT)


def _to_anthropic_messages(messages: list[LLMMessage]) -> list[MessageParam]:
    return [MessageParam(role=m.role, content=m.content) for m in messages]


def _usage_from_anthropic(usage: object) -> LLMUsage:
    return LLMUsage(
        input_tokens=getattr(usage, "input_tokens", 0) or 0,
        output_tokens=getattr(usage, "output_tokens", 0) or 0,
        cache_creation_input_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
        cache_read_input_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
    )


class _AnthropicLLMStream(LLMStream):
    def __init__(self, raw_stream: anthropic.AsyncMessageStream) -> None:
        self._raw_stream = raw_stream

    @property
    def text_stream(self) -> AsyncIterator[str]:
        return self._raw_stream.text_stream

    async def get_final_response(self) -> LLMResponse:
        message = await self._raw_stream.get_final_message()
        text = "".join(block.text for block in message.content if block.type == "text")
        return LLMResponse(
            content=text,
            model=message.model,
            stop_reason=message.stop_reason,
            usage=_usage_from_anthropic(message.usage),
        )


class AnthropicProvider(LLMProvider):
    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            timeout=settings.LLM_REQUEST_TIMEOUT_SECONDS,
        )
        self._model = settings.LLM_MODEL

    async def generate(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
        effort: Effort | None = None,
        enable_thinking: bool | None = None,
    ) -> LLMResponse:
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
                system=system or anthropic.omit,
                messages=_to_anthropic_messages(messages),
                thinking=_thinking_config(enable_thinking),
                output_config=_output_config(effort),
            )
        except anthropic.APIError as exc:
            logger.error("anthropic_generate_failed", error=str(exc))
            raise UpstreamProviderError(f"LLM provider error: {exc}") from exc

        text = "".join(block.text for block in response.content if block.type == "text")
        return LLMResponse(
            content=text,
            model=response.model,
            stop_reason=response.stop_reason,
            usage=_usage_from_anthropic(response.usage),
        )

    def stream(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> AbstractAsyncContextManager[LLMStream]:
        return self._stream_ctx(messages=messages, system=system, max_tokens=max_tokens)

    @asynccontextmanager
    async def _stream_ctx(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None,
        max_tokens: int | None,
    ) -> AsyncIterator[LLMStream]:
        try:
            async with self._client.messages.stream(
                model=self._model,
                max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
                system=system or anthropic.omit,
                messages=_to_anthropic_messages(messages),
                thinking=_thinking_config(None),
                output_config=_output_config(None),
            ) as raw_stream:
                yield _AnthropicLLMStream(raw_stream)
        except anthropic.APIError as exc:
            logger.error("anthropic_stream_failed", error=str(exc))
            raise UpstreamProviderError(f"LLM provider error: {exc}") from exc
