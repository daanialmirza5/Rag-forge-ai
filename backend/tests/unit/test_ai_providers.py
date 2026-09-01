"""Unit tests for the deterministic parts of the AI provider layer — request
shaping and factory wiring. Anything that requires a live network call
(Anthropic/Voyage/Qdrant) is out of scope here; see `docs/PROGRESS.md` for
what's structurally verified vs. exercised live.
"""

import uuid

from app.ai.llm.anthropic_provider import (
    AnthropicProvider,
    _output_config,
    _thinking_config,
    _to_anthropic_messages,
)
from app.ai.llm.base import LLMMessage
from app.ai.llm.factory import get_llm_provider
from app.ai.llm.ollama_provider import _to_ollama_messages
from app.ai.reranking.noop_provider import NoOpRerankProvider
from app.ai.vectorstore.base import VectorPoint
from app.core.config import settings


def test_to_anthropic_messages_preserves_order_and_roles():
    messages = [
        LLMMessage(role="user", content="hello"),
        LLMMessage(role="assistant", content="hi there"),
    ]
    converted = _to_anthropic_messages(messages)
    assert converted == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]


def test_thinking_config_respects_setting_when_not_overridden(monkeypatch):
    monkeypatch.setattr(settings, "LLM_ENABLE_THINKING", True)
    assert _thinking_config(None) == {"type": "adaptive"}

    monkeypatch.setattr(settings, "LLM_ENABLE_THINKING", False)
    assert _thinking_config(None) == {"type": "disabled"}


def test_thinking_config_per_call_override_wins_over_setting(monkeypatch):
    monkeypatch.setattr(settings, "LLM_ENABLE_THINKING", True)
    assert _thinking_config(False) == {"type": "disabled"}

    monkeypatch.setattr(settings, "LLM_ENABLE_THINKING", False)
    assert _thinking_config(True) == {"type": "adaptive"}


def test_output_config_uses_configured_effort_when_not_overridden(monkeypatch):
    monkeypatch.setattr(settings, "LLM_EFFORT", "medium")
    assert _output_config(None) == {"effort": "medium"}


def test_output_config_per_call_override_wins_over_setting(monkeypatch):
    monkeypatch.setattr(settings, "LLM_EFFORT", "high")
    assert _output_config("low") == {"effort": "low"}


def test_llm_factory_returns_singleton():
    assert get_llm_provider() is get_llm_provider()
    assert isinstance(get_llm_provider(), AnthropicProvider)


def test_vector_point_is_a_plain_value_object():
    point = VectorPoint(id=uuid.uuid4(), vector=[0.1, 0.2], payload={"a": 1})
    assert point.payload == {"a": 1}
    assert len(point.vector) == 2


def test_to_ollama_messages_prepends_system_and_preserves_order():
    messages = [
        LLMMessage(role="user", content="hello"),
        LLMMessage(role="assistant", content="hi there"),
    ]
    converted = _to_ollama_messages(messages, "be concise")
    assert converted == [
        {"role": "system", "content": "be concise"},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]


def test_to_ollama_messages_omits_system_when_not_given():
    converted = _to_ollama_messages([LLMMessage(role="user", content="hi")], None)
    assert converted == [{"role": "user", "content": "hi"}]


async def test_noop_rerank_returns_input_order_with_descending_scores():
    results = await NoOpRerankProvider().rerank(
        query="irrelevant", documents=["a", "b", "c"], top_n=2
    )
    assert [r.index for r in results] == [0, 1]
    assert results[0].relevance_score > results[1].relevance_score


async def test_noop_rerank_handles_empty_documents():
    results = await NoOpRerankProvider().rerank(query="q", documents=[], top_n=5)
    assert results == []
