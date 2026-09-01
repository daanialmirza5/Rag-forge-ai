from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=1024)


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1024)


class WorkspaceRead(ORMBase):
    id: UUID
    organization_id: UUID
    name: str
    slug: str
    description: str


class WorkspaceMemberRead(ORMBase):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    user_email: str
    user_full_name: str
    role: str


class WorkspaceMemberAdd(BaseModel):
    user_email: str
    role: str = Field(default="viewer", pattern="^(owner|editor|viewer)$")
