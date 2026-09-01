import pytest

from app.core.exceptions import NotFoundError
from app.storage.local_storage import LocalStorageBackend

pytestmark = pytest.mark.asyncio


@pytest.fixture
def local_backend(tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "STORAGE_LOCAL_PATH", str(tmp_path))
    return LocalStorageBackend()


async def test_save_and_read_roundtrip(local_backend):
    key = "workspace-1/doc-1/report.txt"
    storage_path = await local_backend.save(key=key, content=b"hello world")
    assert storage_path == key

    content = await local_backend.read(storage_path)
    assert content == b"hello world"


async def test_delete_removes_file(local_backend):
    key = "workspace-1/doc-2/file.txt"
    await local_backend.save(key=key, content=b"data")
    await local_backend.delete(key)

    with pytest.raises(NotFoundError):
        await local_backend.read(key)


async def test_read_missing_file_raises_not_found(local_backend):
    with pytest.raises(NotFoundError):
        await local_backend.read("does/not/exist.txt")


async def test_path_traversal_is_rejected(local_backend):
    with pytest.raises(NotFoundError):
        await local_backend.read("../../../../etc/passwd")
