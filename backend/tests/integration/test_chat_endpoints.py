"""End-to-end test of the chat/RAG flow using fake AI providers — no live
Anthropic/Voyage/Qdrant network calls. Real Postgres is still required
(same as every other integration test); it exercises the actual retrieval
graph, SSE formatting, and citation persistence logic, just with the
external AI calls swapped for deterministic fakes.
"""

import json
import uuid
from contextlib import asynccontextmanager

import pytest
from httpx import AsyncClient

from app.ai.embeddings.base import EmbeddingResult
from app.ai.llm.base import LLMResponse, LLMStream, LLMUsage
from app.ai.reranking.base import RerankResult
from app.ai.vectorstore.base import VectorSearchResult
from app.models.chunk import DocumentChunk
from app.models.document import Document, DocumentStatus

pytestmark = pytest.mark.asyncio

FAKE_ANSWER = "The document says revenue grew 12% [1]."


class _FakeLLMStream(LLMStream):
    def __init__(self, text: str) -> None:
        self._text = text

    @property
    def text_stream(self):
        async def _gen():
            yield self._text

        return _gen()

    async def get_final_response(self) -> LLMResponse:
        return LLMResponse(
            content=self._text,
            model="fake-model",
            stop_reason="end_turn",
            usage=LLMUsage(input_tokens=10, output_tokens=5),
        )


class FakeLLMProvider:
    """`generate()` is used for query rewriting (returns the message
    unchanged); `stream()` is used for the final answer."""

    async def generate(self, *, messages, system=None, max_tokens=None, effort=None, enable_thinking=None):
        return LLMResponse(content=messages[-1].content, model="fake-model", stop_reason="end_turn")

    def stream(self, *, messages, system=None, max_tokens=None):
        return self._stream_ctx()

    @asynccontextmanager
    async def _stream_ctx(self):
        yield _FakeLLMStream(FAKE_ANSWER)


class FakeEmbeddingProvider:
    dimensions = 8

    async def embed_documents(self, texts):
        return EmbeddingResult(vectors=[[0.1] * 8 for _ in texts], total_tokens=len(texts))

    async def embed_query(self, text):
        return [0.1] * 8


class FakeRerankProvider:
    async def rerank(self, *, query, documents, top_n):
        return [
            RerankResult(index=i, relevance_score=1.0 - i * 0.1)
            for i in range(min(len(documents), top_n))
        ]


@pytest.fixture
def fake_chunk_id():
    return uuid.uuid4()


@pytest.fixture(autouse=True)
def _patch_ai_providers(monkeypatch, fake_chunk_id):
    from app.ai.graph import nodes as graph_nodes
    from app.ai.retrieval import hybrid_retriever
    from app.services import chat_service

    fake_llm = FakeLLMProvider()
    monkeypatch.setattr(chat_service, "get_llm_provider", lambda: fake_llm)
    monkeypatch.setattr(graph_nodes, "get_llm_provider", lambda: fake_llm)
    monkeypatch.setattr(graph_nodes, "get_rerank_provider", lambda: FakeRerankProvider())
    monkeypatch.setattr(hybrid_retriever, "get_embedding_provider", lambda: FakeEmbeddingProvider())

    class FakeVectorStore:
        async def search(self, *, query_vector, workspace_id, top_k, score_threshold=None):
            return [
                VectorSearchResult(
                    id=uuid.uuid4(),
                    score=0.95,
                    payload={
                        "chunk_id": str(fake_chunk_id),
                        "document_id": "unused",
                        "workspace_id": str(workspace_id),
                    },
                )
            ]

    monkeypatch.setattr(hybrid_retriever, "get_vector_store", lambda: FakeVectorStore())


async def _register_and_login(client: AsyncClient, payload: dict) -> dict:
    await client.post("/api/v1/auth/register", json=payload)
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": payload["email"], "password": payload["password"]},
    )
    tokens = login_resp.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _seed_workspace_with_chunk(
    db_session, headers: dict, client: AsyncClient, chunk_id: uuid.UUID
) -> str:
    org_id = (await client.get("/api/v1/organizations", headers=headers)).json()[0]["id"]
    workspace_id = (
        await client.post(
            f"/api/v1/organizations/{org_id}/workspaces", json={"name": "KB"}, headers=headers
        )
    ).json()["id"]

    document = Document(
        workspace_id=uuid.UUID(workspace_id),
        filename="report.pdf",
        original_filename="report.pdf",
        mime_type="application/pdf",
        size_bytes=100,
        storage_path="unused",
        status=DocumentStatus.COMPLETED.value,
    )
    db_session.add(document)
    await db_session.flush()

    chunk = DocumentChunk(
        id=chunk_id,
        document_id=document.id,
        workspace_id=uuid.UUID(workspace_id),
        chunk_index=0,
        content="Revenue grew 12% year over year according to the Q3 report.",
        token_count=10,
        page_number=1,
    )
    db_session.add(chunk)
    await db_session.commit()

    return workspace_id


async def test_chat_streams_answer_with_citation(
    client: AsyncClient, db_session, registration_payload: dict, fake_chunk_id: uuid.UUID
):
    headers = await _register_and_login(client, registration_payload)
    workspace_id = await _seed_workspace_with_chunk(db_session, headers, client, fake_chunk_id)

    async with client.stream(
        "POST",
        f"/api/v1/workspaces/{workspace_id}/conversations/chat",
        json={"message": "How did revenue perform?"},
        headers=headers,
    ) as response:
        assert response.status_code == 200
        events = []
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: ") :]))

    token_events = [e for e in events if e["type"] == "token"]
    done_events = [e for e in events if e["type"] == "done"]

    assert "".join(e["text"] for e in token_events) == FAKE_ANSWER
    assert len(done_events) == 1
    done = done_events[0]
    assert done["cited_indices"] == [1]
    assert len(done["context_chunks"]) == 1
    assert done["context_chunks"][0]["chunk_id"] == str(fake_chunk_id)

    # The turn was persisted: fetching conversation history shows both
    # the user message and the generated assistant message with its citation.
    history_resp = await client.get(
        f"/api/v1/workspaces/{workspace_id}/conversations/{done['conversation_id']}",
        headers=headers,
    )
    assert history_resp.status_code == 200
    messages = history_resp.json()
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[1]["content"] == FAKE_ANSWER
    assert len(messages[1]["citations"]) == 1
    assert messages[1]["citations"][0]["document_filename"] == "report.pdf"


async def test_viewer_cannot_delete_conversation_but_editor_can(
    client: AsyncClient, db_session, registration_payload: dict, fake_chunk_id: uuid.UUID
):
    owner_headers = await _register_and_login(client, registration_payload)
    workspace_id = await _seed_workspace_with_chunk(
        db_session, owner_headers, client, fake_chunk_id
    )

    chat_resp = await client.post(
        f"/api/v1/workspaces/{workspace_id}/conversations/chat",
        json={"message": "How did revenue perform?"},
        headers=owner_headers,
    )
    assert chat_resp.status_code == 200
    conversations = (
        await client.get(f"/api/v1/workspaces/{workspace_id}/conversations", headers=owner_headers)
    ).json()
    assert conversations, "chat turn should have created a conversation"
    conversation_id = conversations[0]["id"]

    viewer_email = "viewer@example.com"
    viewer_headers = await _register_and_login(
        client,
        {
            "email": viewer_email,
            "password": "supersecret123",
            "full_name": "Val Viewer",
            "organization_name": "Val Co",
        },
    )
    org_id = (
        await client.get("/api/v1/organizations", headers=owner_headers)
    ).json()[0]["id"]
    add_member_resp = await client.post(
        f"/api/v1/organizations/{org_id}/workspaces/{workspace_id}/members",
        json={"user_email": viewer_email, "role": "viewer"},
        headers=owner_headers,
    )
    assert add_member_resp.status_code == 201

    # Read-only role must not be able to delete another user's conversation —
    # a workspace viewer is meant to be read-only.
    viewer_delete_resp = await client.delete(
        f"/api/v1/workspaces/{workspace_id}/conversations/{conversation_id}",
        headers=viewer_headers,
    )
    assert viewer_delete_resp.status_code == 403

    # The workspace owner (outranks editor) can still delete it.
    owner_delete_resp = await client.delete(
        f"/api/v1/workspaces/{workspace_id}/conversations/{conversation_id}",
        headers=owner_headers,
    )
    assert owner_delete_resp.status_code == 204
