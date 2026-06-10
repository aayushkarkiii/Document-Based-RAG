from __future__ import annotations

import asyncio
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import exceptions as qdrant_exceptions
from qdrant_client.http import models as rest

from app.config import Settings

settings = Settings()


class SearchResult:
    def __init__(self, score: float, metadata: dict[str, Any]):
        self.score = score
        self.metadata = metadata


class VectorStoreClient:
    def __init__(self) -> None:
        if settings.vector_store_type != "qdrant":
            raise ValueError("Only qdrant vector store is implemented in this scaffold")

        self.client = QdrantClient(
            url=str(settings.qdrant_url),
            api_key=settings.qdrant_api_key,
            timeout=15,
        )
        self.collection_name = "documents"

    @classmethod
    async def create(cls) -> "VectorStoreClient":
        instance = cls()
        await asyncio.to_thread(instance._ensure_collection)
        return instance

    def _ensure_collection(self) -> None:
        try:
            coll = self.client.get_collection(collection_name=self.collection_name)
        except qdrant_exceptions.ResponseHandlingException as e:
            raise RuntimeError(
                f"Failed to reach Qdrant at {settings.qdrant_url}. Ensure the service is running and the URL is correct."
            ) from e
        except Exception as e:  # handle 404 / collection-not-found from remote Qdrant
            msg = str(e)
            if "Not found" in msg or "doesn't exist" in msg or "doesn\'t exist" in msg:
                self.client.recreate_collection(
                    collection_name=self.collection_name,
                    vectors_config=rest.VectorParams(size=settings.embedding_dimension, distance=rest.Distance.COSINE),
                    timeout=15,
                )
                return
            raise

        if not coll:
            self.client.recreate_collection(
                collection_name=self.collection_name,
                vectors_config=rest.VectorParams(size=settings.embedding_dimension, distance=rest.Distance.COSINE),
                timeout=15,
            )
            return

        if coll.config.params.vectors and coll.config.params.vectors.size != settings.embedding_dimension:
            self.client.recreate_collection(
                collection_name=self.collection_name,
                vectors_config=rest.VectorParams(size=settings.embedding_dimension, distance=rest.Distance.COSINE),
                timeout=15,
            )

    async def upsert_item(self, vector_id: str, vector: list[float], metadata: dict[str, Any]) -> None:
        await asyncio.to_thread(
            self.client.upsert,
            collection_name=self.collection_name,
            points=[rest.PointStruct(id=vector_id, vector=vector, payload=metadata)],
            timeout=15,
        )

    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        query_vector = await self._get_query_embedding(query)
        response = await asyncio.to_thread(
            self.client.query_points,
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit,
            with_payload=True,
            timeout=15,
        )

        return [SearchResult(score=item.score, metadata=item.payload or {}) for item in response.points]

    async def _get_query_embedding(self, query: str) -> list[float]:
        from app.services.embeddings import EmbeddingsClient

        embeddings = EmbeddingsClient()
        vectors = await embeddings.create_embeddings([query])
        return vectors[0]
