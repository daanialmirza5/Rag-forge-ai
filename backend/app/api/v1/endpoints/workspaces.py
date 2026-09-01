import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, DBSession, require_workspace_role
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceMemberAdd,
    WorkspaceMemberRead,
    WorkspaceRead,
    WorkspaceUpdate,
)
from app.services import organization_service, user_service, workspace_service

router = APIRouter(prefix="/organizations/{organization_id}/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceRead, status_code=201)
async def create_workspace(
    organization_id: uuid.UUID,
    payload: WorkspaceCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> WorkspaceRead:
    await organization_service.require_membership(
        db, organization_id=organization_id, user_id=current_user.id
    )
    workspace = await workspace_service.create_workspace(
        db,
        organization_id=organization_id,
        owner_user_id=current_user.id,
        name=payload.name,
        description=payload.description,
    )
    await db.commit()
    return WorkspaceRead.model_validate(workspace)


@router.get("", response_model=list[WorkspaceRead])
async def list_workspaces(
    organization_id: uuid.UUID, current_user: CurrentUser, db: DBSession
) -> list[WorkspaceRead]:
    await organization_service.require_membership(
        db, organization_id=organization_id, user_id=current_user.id
    )
    workspaces = await workspace_service.list_organization_workspaces(db, organization_id)
    return [WorkspaceRead.model_validate(w) for w in workspaces]


@router.get("/{workspace_id}", response_model=WorkspaceRead)
async def get_workspace(
    organization_id: uuid.UUID,
    workspace_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> WorkspaceRead:
    await workspace_service.require_workspace_role(
        db, workspace_id=workspace_id, user_id=current_user.id, minimum_role=WorkspaceRole.VIEWER.value
    )
    workspace = await workspace_service.get_workspace(db, workspace_id)
    if workspace.organization_id != organization_id:
        raise NotFoundError("Workspace not found")
    return WorkspaceRead.model_validate(workspace)


@router.patch("/{workspace_id}", response_model=WorkspaceRead)
async def update_workspace(
    organization_id: uuid.UUID,
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdate,
    db: DBSession,
    _membership: Annotated[WorkspaceMember, Depends(require_workspace_role(WorkspaceRole.EDITOR.value))],
) -> WorkspaceRead:
    workspace = await workspace_service.get_workspace(db, workspace_id)
    if workspace.organization_id != organization_id:
        raise NotFoundError("Workspace not found")
    if payload.name is not None:
        workspace.name = payload.name
    if payload.description is not None:
        workspace.description = payload.description
    await db.flush()
    await db.commit()
    return WorkspaceRead.model_validate(workspace)


@router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberRead])
async def list_members(
    workspace_id: uuid.UUID,
    db: DBSession,
    _membership: Annotated[WorkspaceMember, Depends(require_workspace_role(WorkspaceRole.VIEWER.value))],
) -> list[WorkspaceMemberRead]:
    members = await workspace_service.list_workspace_members(db, workspace_id)
    return [WorkspaceMemberRead.model_validate(m) for m in members]


@router.post("/{workspace_id}/members", response_model=WorkspaceMemberRead, status_code=201)
async def add_member(
    workspace_id: uuid.UUID,
    payload: WorkspaceMemberAdd,
    db: DBSession,
    _membership: Annotated[WorkspaceMember, Depends(require_workspace_role(WorkspaceRole.OWNER.value))],
) -> WorkspaceMemberRead:
    target_user = await user_service.get_user_by_email(db, payload.user_email)
    if target_user is None:
        raise NotFoundError("No user with that email")

    existing = await workspace_service.get_workspace_membership(
        db, workspace_id=workspace_id, user_id=target_user.id
    )
    if existing is not None:
        raise PermissionDeniedError("User is already a member of this workspace")

    member = WorkspaceMember(workspace_id=workspace_id, user_id=target_user.id, role=payload.role)
    db.add(member)
    await db.flush()
    await db.commit()
    return WorkspaceMemberRead.model_validate(member)


@router.delete("/{workspace_id}/members/{member_id}", status_code=204)
async def remove_member(
    workspace_id: uuid.UUID,
    member_id: uuid.UUID,
    db: DBSession,
    _membership: Annotated[WorkspaceMember, Depends(require_workspace_role(WorkspaceRole.OWNER.value))],
) -> None:
    member = await db.get(WorkspaceMember, member_id)
    if member is not None and member.workspace_id == workspace_id:
        await db.delete(member)
        await db.flush()
    await db.commit()
