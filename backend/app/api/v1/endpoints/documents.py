import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.deps import DBSession, require_workspace_role
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.schemas.document import (
    DocumentChunkRead,
    DocumentRead,
    DocumentUploadResponse,
    IngestionJobRead,
)
from app.services import document_service

router = APIRouter(prefix="/workspaces/{workspace_id}/documents", tags=["documents"])

ViewerGuard = Annotated[WorkspaceMember, Depends(require_workspace_role(WorkspaceRole.VIEWER.value))]
EditorGuard = Annotated[WorkspaceMember, Depends(require_workspace_role(WorkspaceRole.EDITOR.value))]


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    workspace_id: uuid.UUID,
    db: DBSession,
    membership: EditorGuard,
    file: Annotated[UploadFile, File()],
) -> DocumentUploadResponse:
    content = await file.read()
    document, job = await document_service.create_document(
        db,
        workspace_id=workspace_id,
        uploaded_by=membership.user_id,
        original_filename=file.filename or "untitled",
        mime_type=file.content_type or "application/octet-stream",
        content=content,
    )
    await db.commit()

    document_service.enqueue_ingestion(document.id)

    return DocumentUploadResponse(
        document=DocumentRead.model_validate(document), ingestion_job_id=job.id
    )


@router.get("", response_model=list[DocumentRead])
async def list_documents(
    workspace_id: uuid.UUID, db: DBSession, _membership: ViewerGuard
) -> list[DocumentRead]:
    documents = await document_service.list_documents(db, workspace_id)
    return [DocumentRead.model_validate(d) for d in documents]


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    workspace_id: uuid.UUID, document_id: uuid.UUID, db: DBSession, _membership: ViewerGuard
) -> DocumentRead:
    document = await document_service.get_document(db, workspace_id, document_id)
    return DocumentRead.model_validate(document)


@router.get("/{document_id}/status", response_model=IngestionJobRead | None)
async def get_ingestion_status(
    workspace_id: uuid.UUID, document_id: uuid.UUID, db: DBSession, _membership: ViewerGuard
) -> IngestionJobRead | None:
    job = await document_service.get_latest_ingestion_job(db, workspace_id, document_id)
    return IngestionJobRead.model_validate(job) if job else None


@router.get("/{document_id}/chunks", response_model=list[DocumentChunkRead])
async def list_chunks(
    workspace_id: uuid.UUID, document_id: uuid.UUID, db: DBSession, _membership: ViewerGuard
) -> list[DocumentChunkRead]:
    chunks = await document_service.list_chunks(db, workspace_id, document_id)
    return [DocumentChunkRead.model_validate(c) for c in chunks]


@router.post("/{document_id}/reingest", response_model=IngestionJobRead)
async def reingest_document(
    workspace_id: uuid.UUID, document_id: uuid.UUID, db: DBSession, _membership: EditorGuard
) -> IngestionJobRead:
    job = await document_service.reingest_document(db, workspace_id, document_id)
    await db.commit()
    document_service.enqueue_ingestion(document_id)
    return IngestionJobRead.model_validate(job)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    workspace_id: uuid.UUID, document_id: uuid.UUID, db: DBSession, _membership: EditorGuard
) -> None:
    await document_service.delete_document(db, workspace_id, document_id)
    await db.commit()
