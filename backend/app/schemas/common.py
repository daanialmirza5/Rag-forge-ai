"""Shared base schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ORMBase(BaseModel):
    """Base for schemas that read directly from SQLAlchemy ORM instances."""

    model_config = ConfigDict(from_attributes=True)


class IDTimestampMixin(BaseModel):
    id: UUID
    created_at: datetime


class Paginated[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int
