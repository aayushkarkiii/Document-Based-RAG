from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class ChunkStrategy(str, Enum):
    fixed = "fixed"
    sentence = "sentence"


class IngestResponse(BaseModel):
    document_id: str
    uploaded_filename: str
    total_chunks: int


class IngestRequest(BaseModel):
    strategy: ChunkStrategy = ChunkStrategy.fixed


class ChatRequest(BaseModel):
    session_id: str
    query: str
    use_memory: bool = True
    max_results: int = 5


class BookingInfo(BaseModel):
    name: str
    email: EmailStr
    date: datetime
    time: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)
    booking: BookingInfo | None = None


class DocumentMetadata(BaseModel):
    title: str | None = None
    source: str | None = None
    page_count: int | None = None


class RatingResponse(BaseModel):
    success: bool
    message: str
    details: dict[str, Any] | None = None
