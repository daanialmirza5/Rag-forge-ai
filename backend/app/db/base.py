"""Aggregator module: imports every model so their tables register on
`Base.metadata` *and* so every `relationship()` string reference (e.g.
`Workspace`'s reference to `"Organization"`) can resolve. Imported by
Alembic's `env.py`, by test fixtures that call `Base.metadata.create_all(...)`,
and by `app/workers/celery_app.py` — the Celery worker process's only import
entry point is that module plus whatever its task modules happen to import
directly, which isn't guaranteed to be the full model set (found by actually
running document ingestion for the first time: `ingestion_tasks.py` imports
`Workspace` but not `Organization`, so a fresh worker process's registry was
incomplete and `Workspace`'s relationship to `Organization` failed to
resolve). Application/service code should still import models directly from
`app.models.*` — this module exists for "does every model actually get
imported somewhere" guarantees, not as a shortcut import path.
"""

from app.db.base_class import Base  # noqa: F401
from app.models.api_key import APIKey  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.chunk import DocumentChunk  # noqa: F401
from app.models.conversation import Conversation  # noqa: F401
from app.models.document import Document  # noqa: F401
from app.models.ingestion_job import IngestionJob  # noqa: F401
from app.models.message import Message, MessageCitation  # noqa: F401
from app.models.organization import Organization, OrganizationMember  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.usage import UsageRecord  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.workspace import Workspace, WorkspaceMember  # noqa: F401
