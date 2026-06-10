from pathlib import Path

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = Field("Document RAG Backend", env="APP_NAME")
    database_url: str = Field("postgresql+asyncpg://postgres:password@localhost:5432/rag_db", env="DATABASE_URL")
    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    redis_namespace: str = Field("chat_memory", env="REDIS_NAMESPACE")
    redis_ttl: int = Field(3600, env="REDIS_TTL")
    redis_history_window: int = Field(10, env="REDIS_HISTORY_WINDOW")
    vector_store_type: str = Field("qdrant", env="VECTOR_STORE_TYPE")
    qdrant_url: HttpUrl | None = Field(None, env="QDRANT_URL")
    qdrant_api_key: str | None = Field(None, env="QDRANT_API_KEY")
    google_api_key: str | None = Field(None, env="GOOGLE_API_KEY")
    gemini_model: str = Field("gemini-2.5-flash", env="GEMINI_MODEL")
    gemini_embedding_model: str = Field("gemini-embedding-2", env="GEMINI_EMBEDDING_MODEL")
    chunk_size: int = Field(500, env="CHUNK_SIZE")
    chunk_overlap: int = Field(50, env="CHUNK_OVERLAP")
    embedding_dimension: int = Field(3072, env="EMBEDDING_DIMENSION")

    class Config:
        env_file = Path(".env")
        env_file_encoding = "utf-8"

    def verify(self) -> None:
        if self.vector_store_type == "qdrant" and not self.qdrant_url:
            raise ValueError("QDRANT_URL is required when VECTOR_STORE_TYPE=qdrant")
        if not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY is required")
