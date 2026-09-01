from celery import Celery

from app.core.config import settings
from app.db.base import Base  # noqa: F401 — see app/db/base.py's docstring

celery_app = Celery(
    "ragforge",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks.ingestion_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # Redeliver a task if the worker dies mid-run rather than silently
    # dropping it; ingestion tasks are idempotent per document (re-running
    # replaces the previous chunk set) so at-least-once delivery is safe.
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=600,
    task_soft_time_limit=540,
)
