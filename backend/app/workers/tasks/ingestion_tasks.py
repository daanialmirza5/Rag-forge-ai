"""Document ingestion pipeline: parse -> chunk -> embed -> index.

Runs as a Celery task. The task body is synchronous (Celery's contract);
`asyncio.run(...)` drives the actual async pipeline, which uses a dedicated
`NullPool` DB engine (`app.db.worker_session`) safe for repeated
`asyncio.run()` calls in one long-lived worker process.

Transient upstream failures (LLM/embedding/vector-store outages —
`UpstreamProviderError`) are retried by Celery with backoff; anything else
(unsupported format, empty document, bad input) is terminal and recorded on
the document immediately, since retrying wouldn't change the outcome.
"""

import asyncio
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select

from app.ai.chunking.recursive_chunker import RecursiveChunker
from app.ai.embeddings.factory import get_embedding_provider
from app.ai.parsers.factory import get_parser_for_mime_type
from app.ai.retrieval.bm25_index import invalidate_workspace_bm25_cache
from app.ai.vectorstore.base import VectorPoint
from app.ai.vectorstore.factory import get_vector_store
from app.core.exceptions import UpstreamProviderError, ValidationAppError
from app.core.logging import get_logger
from app.db.worker_session import worker_db_session
from app.models.chunk import DocumentChunk
from app.models.document import Document, DocumentStatus
from app.models.ingestion_job import IngestionJob, IngestionStage, IngestionStatus
from app.models.usage import UsageEventType
from app.models.workspace import Workspace
from app.services.usage_service import UsageContext, record_usage
from app.storage.factory import get_storage_backend
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


async def _mark_failed(document_id: uuid.UUID, error_message: str) -> None:
    async with worker_db_session() as db:
        document = await db.get(Document, document_id)
        if document is not None:
            document.status = DocumentStatus.FAILED.value
            document.error_message = error_message[:2048]

        job = (
            await db.execute(
                select(IngestionJob)
                .where(IngestionJob.document_id == document_id)
                .order_by(IngestionJob.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if job is not None:
            job.status = IngestionStatus.FAILED.value
            job.error_message = error_message[:2048]
            job.completed_at = datetime.now(UTC)


class _IngestionTask(celery_app.Task):
    """Records terminal (post-retry) failures on the document row — Celery's
    autoretry only re-invokes the task function; it doesn't touch our DB
    state, so the final give-up needs an explicit hook."""

    def on_failure(self, exc: BaseException, task_id: str, args: tuple, kwargs: dict, einfo: object) -> None:
        document_id_str = args[0] if args else kwargs.get("document_id")
        if document_id_str:
            asyncio.run(_mark_failed(uuid.UUID(document_id_str), str(exc)))


@celery_app.task(
    bind=True,
    base=_IngestionTask,
    name="ingestion.process_document",
    autoretry_for=(UpstreamProviderError,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def process_document_task(self, document_id: str) -> None:  # noqa: ANN001
    asyncio.run(_process_document(document_id, celery_task_id=self.request.id))


async def _process_document(document_id_str: str, celery_task_id: str | None) -> None:
    document_id = uuid.UUID(document_id_str)

    async with worker_db_session() as db:
        document = await db.get(Document, document_id)
        if document is None:
            logger.error("ingestion_document_not_found", document_id=document_id_str)
            return

        workspace = await db.get(Workspace, document.workspace_id)
        if workspace is None:
            logger.error("ingestion_workspace_not_found", document_id=document_id_str)
            return

        workspace_id = document.workspace_id
        organization_id = workspace.organization_id
        mime_type = document.mime_type
        storage_path = document.storage_path

        db.add(
            IngestionJob(
                document_id=document.id,
                status=IngestionStatus.RUNNING.value,
                stage=IngestionStage.PARSING.value,
                celery_task_id=celery_task_id,
                started_at=datetime.now(UTC),
            )
        )
        document.status = DocumentStatus.PROCESSING.value
        document.error_message = None

    # --- Parse, chunk, embed, index. No open transaction here — these are
    # slow (I/O + external API) steps and shouldn't hold a DB connection. ---
    try:
        content = await get_storage_backend().read(storage_path)

        parser = get_parser_for_mime_type(mime_type)
        parsed = await asyncio.to_thread(parser.parse, content)
        if parsed.is_empty:
            raise ValidationAppError("No extractable text found in this document")

        chunks = await asyncio.to_thread(RecursiveChunker().chunk, parsed)
        if not chunks:
            raise ValidationAppError("Document produced no chunks after splitting")

        embed_result = await get_embedding_provider().embed_documents(
            [c.content for c in chunks]
        )

        chunk_rows: list[DocumentChunk] = []
        vector_points: list[VectorPoint] = []
        for chunk, vector in zip(chunks, embed_result.vectors, strict=True):
            chunk_id = uuid.uuid4()
            vector_id = uuid.uuid4()
            chunk_rows.append(
                DocumentChunk(
                    id=chunk_id,
                    document_id=document_id,
                    workspace_id=workspace_id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    token_count=chunk.token_count,
                    vector_id=vector_id,
                    page_number=chunk.page_number,
                )
            )
            vector_points.append(
                VectorPoint(
                    id=vector_id,
                    vector=vector,
                    payload={
                        "chunk_id": str(chunk_id),
                        "document_id": str(document_id),
                        "workspace_id": str(workspace_id),
                        "organization_id": str(organization_id),
                    },
                )
            )

        vector_store = get_vector_store()
        # Idempotent: clears any vectors from a prior attempt/re-ingestion
        # before writing the fresh set, so retries never leave duplicates.
        await vector_store.delete_by_document(document_id)
        await vector_store.upsert(vector_points)

    except UpstreamProviderError:
        logger.warning("ingestion_transient_failure", document_id=document_id_str)
        raise  # let Celery's autoretry handle it
    except Exception as exc:  # noqa: BLE001 — terminal: record and stop, don't retry
        logger.error("ingestion_failed", document_id=document_id_str, error=str(exc))
        await _mark_failed(document_id, str(exc))
        return

    # --- Persist the new chunk set and mark the document/job complete. ---
    async with worker_db_session() as db:
        await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
        for row in chunk_rows:
            db.add(row)

        document = await db.get(Document, document_id)
        if document is not None:
            document.status = DocumentStatus.COMPLETED.value
            document.error_message = None

        job = (
            await db.execute(
                select(IngestionJob)
                .where(IngestionJob.document_id == document_id)
                .order_by(IngestionJob.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if job is not None:
            job.status = IngestionStatus.COMPLETED.value
            job.stage = IngestionStage.DONE.value
            job.completed_at = datetime.now(UTC)

        # Embedding cost isn't estimated here (unlike LLM usage in
        # chat_service) — Voyage's published per-token pricing isn't wired
        # into usage_service's pricing table, so cost_usd is left at 0
        # rather than guessing a figure. Token counts are still real.
        await record_usage(
            db,
            context=UsageContext(
                organization_id=organization_id, workspace_id=workspace_id, user_id=None
            ),
            event_type=UsageEventType.DOCUMENT_INGESTED,
            tokens_input=embed_result.total_tokens,
            metadata={"document_id": document_id_str, "chunk_count": len(chunk_rows)},
        )

    await invalidate_workspace_bm25_cache(workspace_id)
    logger.info("ingestion_completed", document_id=document_id_str, chunk_count=len(chunk_rows))
