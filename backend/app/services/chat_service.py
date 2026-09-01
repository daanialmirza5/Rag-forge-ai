"""Chat orchestration: runs the retrieval graph, streams the grounded
answer, and persists the message + citations once the stream completes.

Important: this module opens and manages its **own** DB session
(`AsyncSessionLocal`) rather than accepting one via `Depends(get_db)` from
the caller. A `StreamingResponse`'s body generator runs *after* the FastAPI
path-operation function returns — which is exactly when a `Depends(get_db)`
session would already be committed and closed. Persisting the conversation
turn requires a session that stays open for the lifetime of the stream, so
it's opened here instead.
"""

import re
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.graph.rag_graph import run_retrieval
from app.ai.graph.state import ChatTurn, ContextChunk
from app.ai.llm.base import LLMMessage
from app.ai.llm.factory import get_llm_provider
from app.ai.prompts.rag_prompts import (
    RAG_SYSTEM_PROMPT,
    build_rag_context_block,
    build_rag_user_prompt,
)
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.conversation import Conversation
from app.models.message import Message, MessageCitation, MessageRole
from app.models.usage import UsageEventType
from app.models.workspace import Workspace
from app.services.usage_service import UsageContext, estimate_llm_cost_usd, record_usage

logger = get_logger(__name__)

_CITATION_MARKER_RE = re.compile(r"\[(\d+)\]")
_MAX_HISTORY_MESSAGES = 20
_TITLE_MAX_LENGTH = 80


@dataclass(frozen=True, slots=True)
class ChatStreamToken:
    text: str
    type: Literal["token"] = "token"


@dataclass(frozen=True, slots=True)
class ChatStreamDone:
    message_id: uuid.UUID
    conversation_id: uuid.UUID
    context_chunks: list[ContextChunk] = field(default_factory=list)
    cited_indices: list[int] = field(default_factory=list)
    type: Literal["done"] = "done"


@dataclass(frozen=True, slots=True)
class ChatStreamError:
    message: str
    type: Literal["error"] = "error"


ChatStreamEvent = ChatStreamToken | ChatStreamDone | ChatStreamError


async def _get_or_create_conversation(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID | None,
    first_message: str,
) -> Conversation:
    if conversation_id is not None:
        conversation = await db.get(Conversation, conversation_id)
        if conversation is None or conversation.workspace_id != workspace_id:
            raise NotFoundError("Conversation not found")
        return conversation

    title = first_message.strip().replace("\n", " ")[:_TITLE_MAX_LENGTH] or "New conversation"
    conversation = Conversation(workspace_id=workspace_id, user_id=user_id, title=title)
    db.add(conversation)
    await db.flush()
    return conversation


async def _load_history(db: AsyncSession, conversation_id: uuid.UUID) -> list[ChatTurn]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(_MAX_HISTORY_MESSAGES)
    )
    messages = list(reversed(result.scalars().all()))
    return [ChatTurn(role=m.role, content=m.content) for m in messages]


def _extract_cited_indices(text: str, num_chunks: int) -> list[int]:
    seen: list[int] = []
    for match in _CITATION_MARKER_RE.finditer(text):
        idx = int(match.group(1))
        if 1 <= idx <= num_chunks and idx not in seen:
            seen.append(idx)
    return seen


async def stream_chat_turn(
    *,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID | None,
    user_message: str,
) -> AsyncGenerator[ChatStreamEvent, None]:
    """Owns a DB session for the lifetime of the turn: creates/loads the
    conversation, persists the user message, runs retrieval, streams the
    answer, then persists the assistant message + citations.

    Yields `ChatStreamToken`s as text arrives, then exactly one
    `ChatStreamDone` (success) or `ChatStreamError` (failure after the
    stream had already started, so it can't become an HTTP error status)."""
    async with AsyncSessionLocal() as db:
        try:
            conversation = await _get_or_create_conversation(
                db,
                workspace_id=workspace_id,
                user_id=user_id,
                conversation_id=conversation_id,
                first_message=user_message,
            )
            history = await _load_history(db, conversation.id)

            db.add(
                Message(
                    conversation_id=conversation.id,
                    role=MessageRole.USER.value,
                    content=user_message,
                )
            )
            await db.flush()
            await db.commit()
        except Exception:
            await db.rollback()
            raise

        try:
            rewritten_query, context_chunks = await run_retrieval(
                db,
                workspace_id=conversation.workspace_id,
                history=history,
                user_message=user_message,
            )
            logger.info(
                "rag_retrieval_completed",
                conversation_id=str(conversation.id),
                rewritten_query=rewritten_query,
                chunk_count=len(context_chunks),
            )

            context_block = (
                build_rag_context_block(context_chunks)
                if context_chunks
                else "(no relevant documents found in this workspace)"
            )
            llm_messages = [
                LLMMessage(role=turn["role"], content=turn["content"])  # type: ignore[arg-type]
                for turn in history
            ]
            llm_messages.append(
                LLMMessage(
                    role="user",
                    content=build_rag_user_prompt(context_block=context_block, question=user_message),
                )
            )

            full_text_parts: list[str] = []
            llm_provider = get_llm_provider()
            async with llm_provider.stream(
                messages=llm_messages, system=RAG_SYSTEM_PROMPT
            ) as stream:
                async for chunk in stream.text_stream:
                    full_text_parts.append(chunk)
                    yield ChatStreamToken(text=chunk)
                final_response = await stream.get_final_response()
        except Exception as exc:
            logger.error("chat_turn_generation_failed", error=str(exc))
            yield ChatStreamError(message="Something went wrong generating a response.")
            return

        full_text = "".join(full_text_parts) or final_response.content
        cited_indices = _extract_cited_indices(full_text, len(context_chunks))

        try:
            assistant_message = Message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT.value,
                content=full_text,
                model_used=final_response.model,
                token_usage={
                    "input_tokens": final_response.usage.input_tokens,
                    "output_tokens": final_response.usage.output_tokens,
                    "cache_creation_input_tokens": final_response.usage.cache_creation_input_tokens,
                    "cache_read_input_tokens": final_response.usage.cache_read_input_tokens,
                },
            )
            db.add(assistant_message)
            await db.flush()

            for idx in cited_indices:
                cited_chunk = context_chunks[idx - 1]
                db.add(
                    MessageCitation(
                        message_id=assistant_message.id,
                        chunk_id=uuid.UUID(cited_chunk["chunk_id"]),
                        marker_index=idx,
                        relevance_score=cited_chunk["relevance_score"],
                    )
                )

            workspace = await db.get(Workspace, conversation.workspace_id)
            if workspace is not None:
                await record_usage(
                    db,
                    context=UsageContext(
                        organization_id=workspace.organization_id,
                        workspace_id=workspace.id,
                        user_id=user_id,
                    ),
                    event_type=UsageEventType.CHAT_MESSAGE,
                    tokens_input=final_response.usage.input_tokens,
                    tokens_output=final_response.usage.output_tokens,
                    cost_usd=estimate_llm_cost_usd(
                        model=final_response.model,
                        tokens_input=final_response.usage.input_tokens,
                        tokens_output=final_response.usage.output_tokens,
                    ),
                    metadata={"conversation_id": str(conversation.id)},
                )

            await db.commit()
        except Exception:
            await db.rollback()
            yield ChatStreamError(message="Response generated but could not be saved.")
            return

        yield ChatStreamDone(
            message_id=assistant_message.id,
            conversation_id=conversation.id,
            context_chunks=context_chunks,
            cited_indices=cited_indices,
        )
