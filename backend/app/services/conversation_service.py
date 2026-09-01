import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.chunk import DocumentChunk
from app.models.conversation import Conversation
from app.models.message import Message, MessageCitation


async def list_conversations(db: AsyncSession, workspace_id: uuid.UUID) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.workspace_id == workspace_id)
        .order_by(Conversation.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_conversation_with_messages(
    db: AsyncSession, workspace_id: uuid.UUID, conversation_id: uuid.UUID
) -> Conversation:
    # Citations' `document_*`/`chunk_content` accessors (see `MessageCitation`
    # model) read `chunk` and `chunk.document` off already-loaded objects —
    # both must be eagerly loaded here or those property accesses would need
    # a lazy load, which async SQLAlchemy doesn't support implicitly.
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(
            selectinload(Conversation.messages)
            .selectinload(Message.citations)
            .selectinload(MessageCitation.chunk)
            .selectinload(DocumentChunk.document)
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None or conversation.workspace_id != workspace_id:
        raise NotFoundError("Conversation not found")
    return conversation


async def delete_conversation(
    db: AsyncSession, workspace_id: uuid.UUID, conversation_id: uuid.UUID
) -> None:
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None or conversation.workspace_id != workspace_id:
        raise NotFoundError("Conversation not found")
    await db.delete(conversation)
    await db.flush()
