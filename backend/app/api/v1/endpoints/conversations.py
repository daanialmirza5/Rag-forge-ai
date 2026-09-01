import json
import uuid
from collections.abc import AsyncGenerator
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from app.api.deps import DBSession, require_workspace_role
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.schemas.chat import ChatRequest, ConversationRead, MessageRead
from app.services import chat_service, conversation_service

router = APIRouter(prefix="/workspaces/{workspace_id}/conversations", tags=["chat"])

ViewerGuard = Annotated[WorkspaceMember, Depends(require_workspace_role(WorkspaceRole.VIEWER.value))]
EditorGuard = Annotated[WorkspaceMember, Depends(require_workspace_role(WorkspaceRole.EDITOR.value))]


def _serialize_event(event: chat_service.ChatStreamEvent) -> dict:
    data = asdict(event)
    for key in ("message_id", "conversation_id"):
        if key in data and data[key] is not None:
            data[key] = str(data[key])
    return data


async def _sse_stream(
    *, workspace_id: uuid.UUID, user_id: uuid.UUID, conversation_id: uuid.UUID | None, message: str
) -> AsyncGenerator[bytes, None]:
    async for event in chat_service.stream_chat_turn(
        workspace_id=workspace_id,
        user_id=user_id,
        conversation_id=conversation_id,
        user_message=message,
    ):
        yield f"data: {json.dumps(_serialize_event(event))}\n\n".encode()


@router.post("/chat")
async def chat(
    workspace_id: uuid.UUID, payload: ChatRequest, membership: ViewerGuard
) -> StreamingResponse:
    """Server-Sent Events stream. Each event is `data: {...}\\n\\n` with a
    `type` field: `token` (incremental text), `done` (final message id +
    citations), or `error` (generation/persistence failed after the stream
    had already started, so it can't surface as an HTTP error status)."""
    return StreamingResponse(
        _sse_stream(
            workspace_id=workspace_id,
            user_id=membership.user_id,
            conversation_id=payload.conversation_id,
            message=payload.message,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("", response_model=list[ConversationRead])
async def list_conversations(
    workspace_id: uuid.UUID, db: DBSession, _membership: ViewerGuard
) -> list[ConversationRead]:
    conversations = await conversation_service.list_conversations(db, workspace_id)
    return [ConversationRead.model_validate(c) for c in conversations]


@router.get("/{conversation_id}", response_model=list[MessageRead])
async def get_conversation_messages(
    workspace_id: uuid.UUID, conversation_id: uuid.UUID, db: DBSession, _membership: ViewerGuard
) -> list[MessageRead]:
    conversation = await conversation_service.get_conversation_with_messages(
        db, workspace_id, conversation_id
    )
    return [MessageRead.model_validate(m) for m in conversation.messages]


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    workspace_id: uuid.UUID, conversation_id: uuid.UUID, db: DBSession, _membership: EditorGuard
) -> None:
    await conversation_service.delete_conversation(db, workspace_id, conversation_id)
    await db.commit()
