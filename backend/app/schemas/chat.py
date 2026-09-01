from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


class ConversationCreate(BaseModel):
    title: str = Field(default="New conversation", max_length=255)


class ConversationRead(ORMBase):
    id: UUID
    workspace_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class CitationRead(ORMBase):
    # Was a plain BaseModel — `MessageRead.model_validate(message)` needs
    # every nested schema in from-ORM-attributes mode too, not just the top
    # level, otherwise validating `message.citations` (a list of
    # `MessageCitation` ORM objects) against `list[CitationRead]` fails with
    # "Input should be a valid dictionary or instance of CitationRead".
    # Caught by actually running the chat integration test against a real
    # Postgres for the first time — never exercised through the full API
    # layer before (unit tests covered chat_service in isolation only).
    marker_index: int
    document_id: UUID
    document_filename: str
    chunk_id: UUID
    chunk_content: str
    page_number: int | None
    relevance_score: float


class MessageRead(ORMBase):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    model_used: str | None
    created_at: datetime
    citations: list[CitationRead] = []


class ChatRequest(BaseModel):
    conversation_id: UUID | None = None
    message: str = Field(min_length=1, max_length=8000)
    stream: bool = True
