# Document RAG Backend

A FastAPI backend for **Document Intelligence** and **Conversational RAG**. Upload documents, ask questions, and get answers grounded in your content — with session memory and interview booking detection.

---

## Architecture

```
Client
  │
  ▼
FastAPI (Uvicorn)
  ├──► PostgreSQL   — document metadata, chunks, bookings
  ├──► Qdrant       — vector embeddings + similarity search
  ├──► Redis        — per-session conversation memory
  └──► Gemini API   — embeddings + LLM generation
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | Python 3.12, FastAPI, Uvicorn |
| Database | PostgreSQL, SQLAlchemy (async), asyncpg |
| Vector Store | Qdrant |
| Session Memory | Redis |
| AI | Google Gemini (`gemini-2.5-flash` + `gemini-embedding-2`) |
| Infrastructure | Docker, Docker Compose |

---

## Project Structure

```
root/
├── main.py                  # Entrypoint — mounts routers, health/ready checks
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env
└── app/
    ├── config.py            # Pydantic settings from env
    ├── schemas.py           # Request/response models
    ├── routers/
    │   ├── ingest.py        # POST /ingest/
    │   └── chat.py          # POST /chat/
    ├── services/
    │   ├── document.py      # PDF/TXT text extraction
    │   ├── chunking.py      # Fixed + sentence chunking strategies
    │   ├── embeddings.py    # Gemini embedding calls
    │   ├── llm_client.py    # Prompt building + Gemini generation
    │   ├── vector_store.py  # Qdrant upsert + similarity search
    │   ├── memory.py        # Redis chat history
    │   └── booking.py       # Intent detection + booking persistence
    └── db/
        ├── models.py        # SQLAlchemy models
        ├── session.py       # Async engine + session factory
        └── init_db.py       # Table creation
```

---

## API Reference

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Basic health check |
| `GET` | `/ready` | Checks Qdrant + Gemini connectivity |
| `POST` | `/ingest/` | Upload PDF/TXT → chunk → embed → store |
| `POST` | `/chat/` | Query over documents with session memory |

### POST /ingest/
- **Body**: `multipart/form-data` — `file` (PDF or TXT) + `strategy` (`fixed` or `sentence`)
- **Response**: `document_id`, `uploaded_filename`, `total_chunks`

### POST /chat/
- **Body**:
```json
{
  "session_id": "your-session-id",
  "query": "What is this document about?",
  "use_memory": true,
  "max_results": 5
}
```
- **Response**: `answer`, `sources[]`, `booking` (or null)

---

## RAG Pipeline

### Ingestion
1. Extract text — `pdfplumber` for PDF, UTF-8 decode for TXT
2. Chunk text — fixed (token-based with overlap) or sentence (boundary-aware)
3. Generate embeddings — Gemini batch embedding
4. Store vectors — Qdrant upsert with UUID point IDs
5. Persist metadata — `documents` + `document_chunks` tables in PostgreSQL

### Chat
1. Load history — Redis list keyed by `session_id`
2. Embed query — Gemini embedding
3. Retrieve chunks — Qdrant similarity search (`max_results`)
4. Build prompt — history + retrieved context + query
5. Generate answer — Gemini LLM
6. Detect booking — keyword intent check → regex extraction → persist to PostgreSQL
7. Append memory — store user + assistant messages in Redis

---

## Design Decisions

**Chunking** — two strategies with tradeoffs:

| Strategy | Mechanism | Best for |
|---|---|---|
| `fixed` (default) | Token-based split with configurable overlap | Predictable sizes, fast retrieval |
| `sentence` | Boundary-aware accumulation | Semantic coherence |

Fixed chunker includes guardrails: overlap is clamped below chunk size, and a hard cap prevents runaway chunk counts on large files.

**Async architecture** — all I/O is non-blocking. CPU-bound Gemini calls are offloaded via `asyncio.to_thread()` to avoid blocking the event loop.

**Booking detection** — two-stage: keyword match on the user query triggers regex extraction from the LLM answer, which is then persisted to the `bookings` table.

**Vector IDs** — pure UUIDs (no string prefixes) to satisfy Qdrant's point ID constraints.

---

## Database Schema

| Table | Key Columns |
|---|---|
| `documents` | `id` (UUID), `filename`, `text`, `source`, `uploaded_at` |
| `document_chunks` | `id`, `document_id` (FK), `text`, `meta`, `vector_id` |
| `bookings` | `id`, `name`, `email`, `date`, `time`, `created_at` |

---

## Setup & Running

### Prerequisites
- Docker Desktop
- Google Gemini API key

### Steps

```bash
# 1. Clone the repo
git clone <repo-url> && cd <repo>

# 2. Configure environment
cp .env.example .env
# Add your GOOGLE_API_KEY to .env

# 3. Start all services
docker compose up --build -d

# 4. Initialize database tables
docker compose exec backend python -m app.db.init_db

# 5. Verify
curl http://localhost:8000/health
# → {"status": "ok"}
```

Open `http://localhost:8000/docs` for the interactive Swagger UI.

### Debugging (Docker logs)
Tail backend logs:

```bash
docker compose logs backend -f
```

(You can replace `backend` with the service name if needed.)


---

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:password@postgres:5432/rag_db` | PostgreSQL connection |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `REDIS_NAMESPACE` | `chat_memory` | Key prefix for session memory |
| `REDIS_TTL` | `3600` | Session TTL (seconds) |
| `REDIS_HISTORY_WINDOW` | `10` | Max messages per session |
| `QDRANT_URL` | `http://qdrant:6333` | Qdrant endpoint |
| `GOOGLE_API_KEY` | — | Gemini API key (required) |
| `GEMINI_MODEL` | `gemini-2.5-flash` | LLM model |
| `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-2` | Embedding model |
| `CHUNK_SIZE` | `500` | Tokens per chunk |
| `CHUNK_OVERLAP` | `50` | Overlap between chunks |
| `EMBEDDING_DIMENSION` | `3072` | Qdrant vector size |

---

## Tradeoffs & Future Improvements

- **Alembic migrations** — replace `create_all` with proper schema migrations for production safety
- **pgvector** — use Postgres as the vector store to eliminate Qdrant as a separate dependency
- **Streaming responses** — stream Gemini output for lower perceived latency
- **Structured booking extraction** — replace regex with Gemini function calling / JSON schema for robustness
- **Redis sliding window** — enforce `REDIS_HISTORY_WINDOW` trimming on every write
