import re
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from app.config import Settings

settings = Settings()


class ChunkStrategy(str, Enum):
    fixed = "fixed"
    sentence = "sentence"


@dataclass
class Chunk:
    id: str
    index: int
    text: str
    metadata: dict[str, str]


def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def chunk_text(text: str, strategy: str = ChunkStrategy.fixed.value) -> list[Chunk]:
    if strategy == ChunkStrategy.sentence.value:
        return _sentence_chunking(text)
    return _fixed_chunking(text)


def _fixed_chunking(text: str) -> list[Chunk]:
    # Guardrails to prevent pathological overlap leading to runaway chunk counts / OOM.
    if not text:
        return []

    tokens = text.split()
    if not tokens:
        return []

    chunk_size = max(1, int(settings.chunk_size))
    overlap = max(0, int(settings.chunk_overlap))

    # If overlap >= chunk_size, progress can get stuck (or become extremely slow).
    # Clamp overlap to chunk_size - 1 so each iteration advances.
    if overlap >= chunk_size:
        overlap = chunk_size - 1

    chunks: list[Chunk] = []
    start = 0
    index = 0

    # Hard safety limit (rough upper bound):
    # number of new tokens per chunk ~= (chunk_size - overlap)
    step = max(1, chunk_size - overlap)
    max_chunks = (len(tokens) + step - 1) // step
    max_chunks = min(max_chunks, 10_000)  # absolute cap

    while start < len(tokens) and index < max_chunks:
        end = min(start + chunk_size, len(tokens))
        chunk_text = " ".join(tokens[start:end])
        chunks.append(
            Chunk(
                id=str(uuid.uuid4()),
                index=index,
                text=chunk_text,
                metadata={"strategy": "fixed"},
            )
        )
        index += 1

        prev_start = start
        start = end - overlap

        # Ensure forward progress.
        if start <= prev_start:
            break
        if start < 0:
            start = 0

    return chunks


def _sentence_chunking(text: str) -> list[Chunk]:
    sentences = _split_sentences(text)
    chunks: list[Chunk] = []
    chunk_buffer: list[str] = []
    index = 0

    for sentence in sentences:
        chunk_buffer.append(sentence)
        buffer_text = " ".join(chunk_buffer)
        if len(buffer_text.split()) >= settings.chunk_size:
            chunks.append(
                Chunk(
                    id=str(uuid.uuid4()),
                    index=index,
                    text=buffer_text,
                    metadata={"strategy": "sentence"},
                )
            )
            index += 1
            chunk_buffer = []

    if chunk_buffer:
        chunks.append(
            Chunk(
                id=f"chunk-{index}",
                index=index,
                text=" ".join(chunk_buffer),
                metadata={"strategy": "sentence"},
            )
        )

    return chunks
