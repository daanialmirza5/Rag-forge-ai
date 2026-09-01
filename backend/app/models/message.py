import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.chunk import DocumentChunk
    from app.models.conversation import Conversation


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(Base, UUIDPKMixin):
    """No `updated_at` — messages are append-only."""

    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model_used: Mapped[str | None] = mapped_column(String(64), nullable=True)
    token_usage: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    citations: Mapped[list["MessageCitation"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )


class MessageCitation(Base, UUIDPKMixin):
    __tablename__ = "message_citations"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), index=True
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_chunks.id", ondelete="CASCADE"), index=True
    )
    marker_index: Mapped[int] = mapped_column(Integer, nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    message: Mapped["Message"] = relationship(back_populates="citations")
    chunk: Mapped["DocumentChunk"] = relationship()

    # Denormalized read-only accessors for the API schema (`CitationRead`).
    # Only safe to access when `chunk` (and `chunk.document`) were eagerly
    # loaded (see `conversation_service.get_conversation_with_messages`) —
    # lazy-loading a relationship attribute on an async session outside a
    # loaded-object context raises `MissingGreenlet`, so these must never be
    # the trigger for a first load.
    @property
    def document_id(self) -> uuid.UUID:
        return self.chunk.document_id

    @property
    def document_filename(self) -> str:
        return self.chunk.document.original_filename

    @property
    def chunk_content(self) -> str:
        return self.chunk.content

    @property
    def page_number(self) -> int | None:
        return self.chunk.page_number
