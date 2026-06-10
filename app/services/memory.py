import json
from typing import Any

import redis.asyncio as redis

from app.config import Settings

settings = Settings()


class ChatMemoryStore:
    def __init__(self) -> None:
        self.client = redis.from_url(settings.redis_url, decode_responses=True)

    def _key(self, session_id: str) -> str:
        return f"{settings.redis_namespace}:{session_id}"

    async def append_message(self, session_id: str, role: str, content: str) -> None:
        payload = json.dumps({"role": role, "content": content})
        await self.client.rpush(self._key(session_id), payload)

    async def get_history(self, session_id: str) -> list[dict[str, str]]:
        raw = await self.client.lrange(self._key(session_id), 0, -1)
        return [json.loads(item) for item in raw]

    async def clear_history(self, session_id: str) -> None:
        await self.client.delete(self._key(session_id))
