"""Ollama implementation of `LLMProvider` — a free, fully local alternative to
Anthropic Claude for development/demo use (no API key, no per-token cost).

Talks to Ollama's REST API directly over `httpx` rather than adding the
`ollama` PyPI package as a dependency — the API surface used here (`/api/chat`,
streaming and non-streaming) is small and stable.

`effort`/`enable_thinking` are part of the `LLMProvider` interface for
Anthropic's adaptive-thinking feature, which local models don't have; they're
accepted for interface compatibility and otherwise ignored here.
"""

import json
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager

import httpx

from app.ai.llm.base import Effort, LLMMessage, LLMProvider, LLMResponse, LLMStream, LLMUsage
from app.core.config import settings
from app.core.exceptions import UpstreamProviderError
from app.core.logging import get_logger

logger = get_logger(__name__)


def _to_ollama_messages(messages: list[LLMMessage], system: str | None) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    if system:
        result.append({"role": "system", "content": system})
    result.extend({"role": m.role, "content": m.content} for m in messages)
    return result


class _OllamaLLMStream(LLMStream):
    def __init__(self, response: httpx.Response, model: str) -> None:
        self._response = response
        self._model = model
        self._content_parts: list[str] = []
        self._final_line: dict = {}

    @property
    def text_stream(self) -> AsyncIterator[str]:
        return self._iter_text()

    async def _iter_text(self) -> AsyncIterator[str]:
        async for line in self._response.aiter_lines():
            if not line:
                continue
            data = json.loads(line)
            chunk = data.get("message", {}).get("content", "")
            if chunk:
                self._content_parts.append(chunk)
                yield chunk
            if data.get("done"):
                self._final_line = data

    async def get_final_response(self) -> LLMResponse:
        return LLMResponse(
            content="".join(self._content_parts),
            model=self._final_line.get("model", self._model),
            stop_reason=self._final_line.get("done_reason"),
            usage=LLMUsage(
                input_tokens=self._final_line.get("prompt_eval_count", 0),
                output_tokens=self._final_line.get("eval_count", 0),
            ),
        )


class OllamaProvider(LLMProvider):
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.OLLAMA_BASE_URL, timeout=settings.LLM_REQUEST_TIMEOUT_SECONDS
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
            response = await self._client.post(
                "/api/chat",
                json={
                    "model": self._model,
                    "messages": _to_ollama_messages(messages, system),
                    "stream": False,
                    "options": {"num_predict": max_tokens or settings.LLM_MAX_TOKENS},
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("ollama_generate_failed", error=str(exc))
            raise UpstreamProviderError(f"LLM provider error: {exc}") from exc

        data = response.json()
        return LLMResponse(
            content=data.get("message", {}).get("content", ""),
            model=data.get("model", self._model),
            stop_reason=data.get("done_reason"),
            usage=LLMUsage(
                input_tokens=data.get("prompt_eval_count", 0),
                output_tokens=data.get("eval_count", 0),
            ),
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
            async with self._client.stream(
                "POST",
                "/api/chat",
                json={
                    "model": self._model,
                    "messages": _to_ollama_messages(messages, system),
                    "stream": True,
                    "options": {"num_predict": max_tokens or settings.LLM_MAX_TOKENS},
                },
            ) as response:
                response.raise_for_status()
                yield _OllamaLLMStream(response, self._model)
        except httpx.HTTPError as exc:
            logger.error("ollama_stream_failed", error=str(exc))
            raise UpstreamProviderError(f"LLM provider error: {exc}") from exc
