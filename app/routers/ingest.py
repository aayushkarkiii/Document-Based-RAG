from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, DocumentChunk
from app.db.session import get_db
from app.schemas import IngestRequest, IngestResponse
from app.services.chunking import chunk_text
from app.services.document import extract_document_text
from app.services.embeddings import EmbeddingsClient
from app.services.vector_store import VectorStoreClient

router = APIRouter()

vector_client: VectorStoreClient | None = None


def get_vector_client() -> VectorStoreClient:  # not async
    global vector_client
    if vector_client is None:
        vector_client = VectorStoreClient()  # not .create()
    return vector_client


@router.post("/", response_model=IngestResponse)
async def ingest_document(
    strategy: IngestRequest = Depends(),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> IngestResponse:
    if file.content_type not in {"application/pdf", "text/plain"}:
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are accepted")

    text = await extract_document_text(file)
    chunks = chunk_text(text, strategy.strategy)
    embeddings_client = EmbeddingsClient()
    try:
        embeddings = await embeddings_client.create_embeddings([chunk.text for chunk in chunks])
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Embedding service error: {exc}") from exc

    document = Document(filename=file.filename, text=text, source=file.filename)
    db.add(document)
    await db.flush()

    vc = get_vector_client()  # call once, store in variable
    for chunk, vector in zip(chunks, embeddings):
        chunk_record = DocumentChunk(
            document_id=document.id,
            text=chunk.text,
            meta=str(chunk.metadata),
            vector_id=chunk.id,
        )
        db.add(chunk_record)
        try:
            await vc.upsert_item(chunk.id, vector, {
                "document_id": document.id,
                "filename": file.filename,
                "chunk_index": chunk.index,
                "text": chunk.text,
            })
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Vector store error: {exc}") from exc

    await db.commit()
    return IngestResponse(
        document_id=document.id,
        uploaded_filename=file.filename,
        total_chunks=len(chunks),
    )