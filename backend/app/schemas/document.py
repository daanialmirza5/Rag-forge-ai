from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMBase


class DocumentRead(ORMBase):
    id: UUID
    workspace_id: UUID
    filename: str
    original_filename: str
    mime_type: str
    size_bytes: int
    status: str
    error_message: str | None
    created_at: datetime


class DocumentChunkRead(ORMBase):
    id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    token_count: int
    page_number: int | None


class IngestionJobRead(ORMBase):
    id: UUID
    document_id: UUID
    status: str
    stage: str
    error_message: str | None


class DocumentUploadResponse(BaseModel):
    document: DocumentRead
    ingestion_job_id: UUID
