"""S3-compatible object storage backend, selected via `STORAGE_BACKEND=s3`.

`boto3` is not a hard dependency of this project (local storage is the
default); it's imported lazily so choosing local storage never requires
installing it. `boto3` has no native asyncio client, so calls run in a
thread via `asyncio.to_thread`.
"""

import asyncio

from app.core.config import settings
from app.core.exceptions import NotFoundError, UpstreamProviderError
from app.storage.base import StorageBackend


class S3StorageBackend(StorageBackend):
    def __init__(self) -> None:
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError(
                "STORAGE_BACKEND=s3 requires the `boto3` package: pip install boto3"
            ) from exc

        self._client = boto3.client(
            "s3",
            region_name=settings.S3_REGION or None,
            endpoint_url=settings.S3_ENDPOINT_URL or None,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY or None,
        )
        self._bucket = settings.S3_BUCKET

    async def save(self, *, key: str, content: bytes) -> str:
        try:
            await asyncio.to_thread(
                self._client.put_object, Bucket=self._bucket, Key=key, Body=content
            )
        except Exception as exc:  # noqa: BLE001 — boto3 raises botocore.exceptions.ClientError
            raise UpstreamProviderError(f"Storage error: {exc}") from exc
        return key

    async def read(self, storage_path: str) -> bytes:
        try:
            response = await asyncio.to_thread(
                self._client.get_object, Bucket=self._bucket, Key=storage_path
            )
        except Exception as exc:  # noqa: BLE001
            if type(exc).__name__ == "NoSuchKey" or "NoSuchKey" in str(exc):
                raise NotFoundError("File not found in storage") from exc
            raise UpstreamProviderError(f"Storage error: {exc}") from exc
        return await asyncio.to_thread(response["Body"].read)

    async def delete(self, storage_path: str) -> None:
        try:
            await asyncio.to_thread(
                self._client.delete_object, Bucket=self._bucket, Key=storage_path
            )
        except Exception as exc:  # noqa: BLE001
            raise UpstreamProviderError(f"Storage error: {exc}") from exc
