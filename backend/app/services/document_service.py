"""Document upload/list/delete + enqueuing the ingestion pipeline.

The Celery import (`process_document_task`) is deferred to call time inside
`create_document` rather than imported at module scope, so importing this
service (e.g. from API request handlers) never pulls in Celery's eager
worker-registration side effects on the request path.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.parsers.factory import is_supported_mime_type
from app.ai.retrieval.bm25_index import invalidate_workspace_bm25_cache
from app.ai.vectorstore.factory import get_vector_store
from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.chunk import DocumentChunk
from app.models.document import Document, DocumentStatus
from app.models.ingestion_job import IngestionJob, IngestionStatus
from app.storage.factory import get_storage_backend


def _validate_upload(*, mime_type: str, size_bytes: int) -> None:
    if not is_supported_mime_type(mime_type):
        raise ValidationAppError(f"Unsupported file type: {mime_type}")
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if size_bytes > max_bytes:
        raise ValidationAppError(
            f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB upload limit"
        )
    if size_bytes == 0:
        raise ValidationAppError("Uploaded file is empty")


async def create_document(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    uploaded_by: uuid.UUID,
    original_filename: str,
    mime_type: str,
    content: bytes,
) -> tuple[Document, IngestionJob]:
    _validate_upload(mime_type=mime_type, size_bytes=len(content))

    document_id = uuid.uuid4()
    storage_key = f"{workspace_id}/{document_id}/{original_filename}"
    storage_path = await get_storage_backend().save(key=storage_key, content=content)

    document = Document(
        id=document_id,
        workspace_id=workspace_id,
        uploaded_by=uploaded_by,
        filename=original_filename,
        original_filename=original_filename,
        mime_type=mime_type,
        size_bytes=len(content),
        storage_path=storage_path,
        status=DocumentStatus.PENDING.value,
    )
    db.add(document)
    await db.flush()

    job = IngestionJob(document_id=document.id, status=IngestionStatus.PENDING.value)
    db.add(job)
    await db.flush()

    return document, job


def enqueue_ingestion(document_id: uuid.UUID) -> None:
    from app.workers.tasks.ingestion_tasks import process_document_task

    process_document_task.delay(str(document_id))


async def get_document(db: AsyncSession, workspace_id: uuid.UUID, document_id: uuid.UUID) -> Document:
    """`workspace_id` is not just a filter — it's the tenant-isolation check.
    A document that exists but belongs to a different workspace must 404,
    not leak its existence to a caller who only has access to `workspace_id`."""
    document = await db.get(Document, document_id)
    if document is None or document.workspace_id != workspace_id:
        raise NotFoundError("Document not found")
    return document


async def list_documents(db: AsyncSession, workspace_id: uuid.UUID) -> list[Document]:
    result = await db.execute(
        select(Document)
        .where(Document.workspace_id == workspace_id)
        .order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


async def list_chunks(
    db: AsyncSession, workspace_id: uuid.UUID, document_id: uuid.UUID
) -> list[DocumentChunk]:
    await get_document(db, workspace_id, document_id)  # tenant-isolation check
    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    return list(result.scalars().all())


async def get_latest_ingestion_job(
    db: AsyncSession, workspace_id: uuid.UUID, document_id: uuid.UUID
) -> IngestionJob | None:
    await get_document(db, workspace_id, document_id)  # tenant-isolation check
    result = await db.execute(
        select(IngestionJob)
        .where(IngestionJob.document_id == document_id)
        .order_by(IngestionJob.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def delete_document(db: AsyncSession, workspace_id: uuid.UUID, document_id: uuid.UUID) -> None:
    document = await get_document(db, workspace_id, document_id)

    await get_vector_store().delete_by_document(document_id)
    await get_storage_backend().delete(document.storage_path)

    await db.delete(document)  # cascades to chunks + ingestion_jobs via FK ondelete
    await db.flush()
    await invalidate_workspace_bm25_cache(workspace_id)


async def reingest_document(
    db: AsyncSession, workspace_id: uuid.UUID, document_id: uuid.UUID
) -> IngestionJob:
    document = await get_document(db, workspace_id, document_id)
    document.status = DocumentStatus.PENDING.value
    document.error_message = None

    job = IngestionJob(document_id=document.id, status=IngestionStatus.PENDING.value)
    db.add(job)
    await db.flush()
    return job
