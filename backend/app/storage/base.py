"""Object storage abstraction for uploaded documents.

`key` is a logical path (`{workspace_id}/{document_id}/{filename}`) chosen by
the caller; the backend decides how that maps to an actual location and
returns an opaque `storage_path` string that must be passed back unchanged
to `read`/`delete` (for local storage these happen to be the same string;
for S3 a backend could return a versioned URI instead).
"""

from abc import ABC, abstractmethod


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, *, key: str, content: bytes) -> str: ...

    @abstractmethod
    async def read(self, storage_path: str) -> bytes: ...

    @abstractmethod
    async def delete(self, storage_path: str) -> None: ...
