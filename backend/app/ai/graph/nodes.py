"""Node functions for the retrieval graph. Each node reads/returns partial
`RAGState` updates; LangGraph merges them. Per-request dependencies (the DB
session) are threaded through `RunnableConfig.configurable` rather than
graph state, since a live `AsyncSession` doesn't belong in workflow state —
see `app/ai/graph/rag_graph.py` for how the config is built.
"""

import uuid

from langchain_core.runnables import RunnableConfig
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.graph.state import ContextChunk, RAGState
from app.ai.llm.base import LLMMessage
from app.ai.llm.factory import get_llm_provider
from app.ai.prompts.rag_prompts import (
    QUERY_REWRITE_SYSTEM_PROMPT,
    build_query_rewrite_user_prompt,
)
from app.ai.reranking.factory import get_rerank_provider
from app.ai.retrieval.hybrid_retriever import hybrid_retrieve
from app.core.config import settings
from app.core.logging import get_logger
from app.models.chunk import DocumentChunk
from app.models.document import Document

logger = get_logger(__name__)


def _db_from_config(config: RunnableConfig) -> AsyncSession:
    return config["configurable"]["db"]


async def rewrite_query_node(state: RAGState, config: RunnableConfig) -> dict:
    history = state["history"][-settings.RETRIEVAL_HISTORY_TURNS_FOR_REWRITE :]
    if not history:
        return {"rewritten_query": state["user_message"]}

    history_text = "\n".join(f"{turn['role']}: {turn['content']}" for turn in history)
    response = await get_llm_provider().generate(
        messages=[
            LLMMessage(
                role="user",
                content=build_query_rewrite_user_prompt(
                    history_text=history_text, latest_message=state["user_message"]
                ),
            )
        ],
        system=QUERY_REWRITE_SYSTEM_PROMPT,
        max_tokens=200,
        effort="low",
        enable_thinking=False,
    )
    rewritten = response.content.strip() or state["user_message"]
    return {"rewritten_query": rewritten}


async def hybrid_retrieve_node(state: RAGState, config: RunnableConfig) -> dict:
    db = _db_from_config(config)
    workspace_id = uuid.UUID(state["workspace_id"])

    retrieved = await hybrid_retrieve(
        db,
        workspace_id=workspace_id,
        query=state["rewritten_query"],
        dense_top_k=settings.RETRIEVAL_DENSE_TOP_K,
        sparse_top_k=settings.RETRIEVAL_SPARSE_TOP_K,
        fused_top_k=settings.RETRIEVAL_FUSED_TOP_K,
    )
    if not retrieved:
        return {"context_chunks": []}

    chunk_ids = [r.chunk_id for r in retrieved]
    result = await db.execute(
        select(DocumentChunk, Document.original_filename)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.id.in_(chunk_ids))
    )
    by_id = {chunk.id: (chunk, filename) for chunk, filename in result.all()}

    context_chunks: list[ContextChunk] = []
    for r in retrieved:
        pair = by_id.get(r.chunk_id)
        if pair is None:
            continue  # chunk was deleted between vector search and this fetch
        chunk, filename = pair
        context_chunks.append(
            ContextChunk(
                chunk_id=str(chunk.id),
                document_id=str(chunk.document_id),
                document_filename=filename,
                content=chunk.content,
                page_number=chunk.page_number,
                relevance_score=r.fused_score,
            )
        )
    return {"context_chunks": context_chunks}


async def rerank_node(state: RAGState, config: RunnableConfig) -> dict:
    candidates = state["context_chunks"]
    if not candidates:
        return {"context_chunks": []}

    results = await get_rerank_provider().rerank(
        query=state["rewritten_query"],
        documents=[c["content"] for c in candidates],
        top_n=settings.RETRIEVAL_RERANK_TOP_N,
    )

    reranked: list[ContextChunk] = []
    for r in results:
        original = candidates[r.index]
        reranked.append(
            ContextChunk(
                chunk_id=original["chunk_id"],
                document_id=original["document_id"],
                document_filename=original["document_filename"],
                content=original["content"],
                page_number=original["page_number"],
                relevance_score=r.relevance_score,
            )
        )
    return {"context_chunks": reranked}
