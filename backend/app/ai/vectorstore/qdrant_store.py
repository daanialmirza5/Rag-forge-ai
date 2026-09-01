import uuid

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels
from qdrant_client.http.exceptions import ApiException

from app.ai.vectorstore.base import VectorPoint, VectorSearchResult, VectorStore
from app.core.config import settings
from app.core.exceptions import UpstreamProviderError
from app.core.logging import get_logger

logger = get_logger(__name__)

_WORKSPACE_ID_FIELD = "workspace_id"
_DOCUMENT_ID_FIELD = "document_id"


class QdrantVectorStore(VectorStore):
    def __init__(self) -> None:
        self._client = AsyncQdrantClient(
            url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None
        )
        self._collection = settings.QDRANT_COLLECTION_NAME
        self._vector_size = settings.EMBEDDING_DIMENSIONS

    async def ensure_collection(self) -> None:
        try:
            exists = await self._client.collection_exists(self._collection)
            if not exists:
                await self._client.create_collection(
                    collection_name=self._collection,
                    vectors_config=qmodels.VectorParams(
                        size=self._vector_size, distance=qmodels.Distance.COSINE
                    ),
                )
                logger.info("qdrant_collection_created", collection=self._collection)

            for field_name, schema in (
                (_WORKSPACE_ID_FIELD, qmodels.PayloadSchemaType.KEYWORD),
                (_DOCUMENT_ID_FIELD, qmodels.PayloadSchemaType.KEYWORD),
            ):
                await self._client.create_payload_index(
                    collection_name=self._collection,
                    field_name=field_name,
                    field_schema=schema,
                )
        except ApiException as exc:
            logger.error("qdrant_ensure_collection_failed", error=str(exc))
            raise UpstreamProviderError(f"Vector store error: {exc}") from exc

    async def upsert(self, points: list[VectorPoint]) -> None:
        if not points:
            return
        try:
            await self._client.upsert(
                collection_name=self._collection,
                points=[
                    qmodels.PointStruct(id=str(p.id), vector=p.vector, payload=p.payload)
                    for p in points
                ],
            )
        except ApiException as exc:
            logger.error("qdrant_upsert_failed", error=str(exc))
            raise UpstreamProviderError(f"Vector store error: {exc}") from exc

    async def search(
        self,
        *,
        query_vector: list[float],
        workspace_id: uuid.UUID,
        top_k: int,
        score_threshold: float | None = None,
    ) -> list[VectorSearchResult]:
        try:
            response = await self._client.query_points(
                collection_name=self._collection,
                query=query_vector,
                query_filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key=_WORKSPACE_ID_FIELD,
                            match=qmodels.MatchValue(value=str(workspace_id)),
                        )
                    ]
                ),
                limit=top_k,
                score_threshold=score_threshold,
                with_payload=True,
            )
        except ApiException as exc:
            logger.error("qdrant_search_failed", error=str(exc))
            raise UpstreamProviderError(f"Vector store error: {exc}") from exc

        return [
            VectorSearchResult(id=uuid.UUID(str(point.id)), score=point.score, payload=point.payload or {})
            for point in response.points
        ]

    async def delete_by_document(self, document_id: uuid.UUID) -> None:
        try:
            await self._client.delete(
                collection_name=self._collection,
                points_selector=qmodels.FilterSelector(
                    filter=qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key=_DOCUMENT_ID_FIELD,
                                match=qmodels.MatchValue(value=str(document_id)),
                            )
                        ]
                    )
                ),
            )
        except ApiException as exc:
            logger.error("qdrant_delete_failed", error=str(exc))
            raise UpstreamProviderError(f"Vector store error: {exc}") from exc
