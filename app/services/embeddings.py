import asyncio
from typing import Iterable

import google.genai as genai

from app.config import Settings

settings = Settings()
genai_client = genai.Client(
    api_key=settings.google_api_key,
    http_options=genai.types.HttpOptions(timeout=15000),
)


class EmbeddingsClient:
    async def create_embeddings(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        return await asyncio.wait_for(
            asyncio.to_thread(self._create_embeddings_sync, texts),
            timeout=30,
        )

    async def health_check(self) -> bool:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._test_embedding_sync),
                timeout=30,
            )
        except Exception as exc:
            raise RuntimeError(f"Embedding service health check failed: {exc}") from exc

    def _test_embedding_sync(self) -> bool:
        response = genai_client.models.embed_content(
            model=settings.gemini_embedding_model,
            contents=["health-check"],
        )
        return bool(response.embeddings)

    def _create_embeddings_sync(self, texts: list[str]) -> list[list[float]]:
        response = genai_client.models.embed_content(
            model=settings.gemini_embedding_model,
            contents=texts,
        )

        return [embedding.values or [] for embedding in response.embeddings or []]
