from functools import lru_cache

from app.core.config import settings
from app.core.exceptions import AppError
from app.storage.base import StorageBackend


@lru_cache
def get_storage_backend() -> StorageBackend:
    if settings.STORAGE_BACKEND == "local":
        from app.storage.local_storage import LocalStorageBackend

        return LocalStorageBackend()
    if settings.STORAGE_BACKEND == "s3":
        from app.storage.s3_storage import S3StorageBackend

        return S3StorageBackend()
    raise AppError(f"Unknown storage backend: {settings.STORAGE_BACKEND}")
