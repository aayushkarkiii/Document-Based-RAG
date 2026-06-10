from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas import BookingInfo, ChatRequest, ChatResponse
from app.services.booking import detect_booking_intent, save_booking_info
from app.services.llm_client import LLMClient
from app.services.memory import ChatMemoryStore
from app.services.vector_store import VectorStoreClient

router = APIRouter()
vector_client: VectorStoreClient | None = None
memory_store = ChatMemoryStore()
llm_client = LLMClient()


async def get_vector_client() -> VectorStoreClient:
    global vector_client
    if vector_client is None:
        vector_client = await VectorStoreClient.create()
    return vector_client


@router.post("/", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, db: AsyncSession = Depends(get_db)) -> ChatResponse:
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty")

    history = []
    if request.use_memory:
        history = await memory_store.get_history(request.session_id)

    vector_client = await get_vector_client()
    search_results = await vector_client.search(request.query, limit=request.max_results)
    prompt = llm_client.build_prompt(request.query, history, search_results)
    answer_text = await llm_client.generate(prompt)

    booking_info: BookingInfo | None = None
    if detect_booking_intent(request.query):
        booking_info = await save_booking_info(answer_text, db)

    if request.use_memory:
        await memory_store.append_message(request.session_id, "user", request.query)
        await memory_store.append_message(request.session_id, "assistant", answer_text)

    return ChatResponse(
        answer=answer_text,
        sources=[str(result.metadata) for result in search_results],
        booking=booking_info,
    )


@router.post("/text", response_model=ChatResponse)
async def chat_text_endpoint(
    message: str = Body(..., media_type="text/plain"),
    session_id: str | None = Query(None, description="Optional session id for chat memory"),
    use_memory: bool = Query(True, description="Keep conversation memory for the session"),
    max_results: int = Query(5, ge=1, le=20, description="Number of retrieval results"),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    if not message.strip():
        raise HTTPException(status_code=400, detail="Message must not be empty")

    request = ChatRequest(
        session_id=session_id or "raw-session",
        query=message,
        use_memory=use_memory,
        max_results=max_results,
    )
    return await chat_endpoint(request, db)
