import asyncio
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.storage.base import StorageBackend


class LocalStorageBackend(StorageBackend):
    """Stores files on the local filesystem under `STORAGE_LOCAL_PATH`.
    Fine for single-node dev/demo deployments; use `s3` for anything
    multi-replica since local disk isn't shared across containers."""

    def __init__(self) -> None:
        self._root = Path(settings.STORAGE_LOCAL_PATH).resolve()

    def _resolve(self, key: str) -> Path:
        # Defense in depth: a `key` is always constructed server-side (see
        # `document_service.build_storage_key`), but guard against path
        # traversal regardless of caller.
        candidate = (self._root / key).resolve()
        if not candidate.is_relative_to(self._root):
            raise NotFoundError("Invalid storage path")
        return candidate

    async def save(self, *, key: str, content: bytes) -> str:
        path = self._resolve(key)

        def _write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)

        await asyncio.to_thread(_write)
        return key

    async def read(self, storage_path: str) -> bytes:
        path = self._resolve(storage_path)
        if not path.is_file():
            raise NotFoundError("File not found in storage")
        return await asyncio.to_thread(path.read_bytes)

    async def delete(self, storage_path: str) -> None:
        path = self._resolve(storage_path)

        def _delete() -> None:
            path.unlink(missing_ok=True)

        await asyncio.to_thread(_delete)
