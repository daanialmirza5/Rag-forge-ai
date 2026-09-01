from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


class AdminOrganizationRead(BaseModel):
    id: UUID
    name: str
    slug: str
    plan_tier: str
    member_count: int
    workspace_count: int
    created_at: datetime


class AdminOrganizationPlanUpdate(BaseModel):
    plan_tier: str = Field(pattern="^(free|pro|enterprise)$")


class AdminUserRead(ORMBase):
    id: UUID
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool
    email_verified: bool
    created_at: datetime


class AdminUserActiveUpdate(BaseModel):
    is_active: bool


class AdminUserSuperuserUpdate(BaseModel):
    is_superuser: bool


class AdminAuditLogRead(ORMBase):
    id: UUID
    organization_id: UUID | None
    user_id: UUID | None
    action: str
    resource_type: str
    resource_id: UUID | None
    ip_address: str | None
    created_at: datetime
