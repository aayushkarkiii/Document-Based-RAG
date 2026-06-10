from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.routers import chat, ingest
from app.config import Settings
from app.services.embeddings import EmbeddingsClient
from app.services.vector_store import VectorStoreClient

settings = Settings()
app = FastAPI(title="Document RAG Backend", version="0.1.0")

app.include_router(ingest.router, prefix="/ingest", tags=["ingestion"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])


@app.on_event("startup")
async def startup_event() -> None:
    settings.verify()
    await VectorStoreClient.create()


@app.get("/ready")
async def readiness_check() -> dict[str, object]:
    try:
        await VectorStoreClient.create()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Qdrant readiness failure: {exc}") from exc

    try:
        embeddings = EmbeddingsClient()
        await embeddings.health_check()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Embedding readiness failure: {exc}") from exc

    return {
        "status": "ok",
        "qdrant": True,
        "embeddings": True,
    }


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
