from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse

from app.routers import chat, ingest
from app.config import Settings

settings = Settings()
app = FastAPI(title="Document RAG Backend", version="0.1.0")

app.include_router(ingest.router, prefix="/ingest", tags=["ingestion"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])


@app.on_event("startup")
async def startup_event() -> None:
    settings.verify()


@app.get("/")
def root() -> JSONResponse:
    return JSONResponse({
        "message": "Welcome to Document RAG Backend",
        "version": "0.1.0",
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
            "ingest": "/ingest",
            "docs": "/docs",
        }
    })


@app.get("/favicon.ico")
def favicon() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
