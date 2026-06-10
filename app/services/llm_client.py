from __future__ import annotations

import asyncio
from typing import Any

import google.genai as genai

from app.config import Settings
from app.services.vector_store import SearchResult

settings = Settings()
genai_client = genai.Client(api_key=settings.google_api_key)


class LLMClient:
    def build_prompt(
        self,
        query: str,
        history: list[dict[str, str]],
        search_results: list[SearchResult],
    ) -> str:
        history_text = "\n".join([f"{item['role']}: {item['content']}" for item in history])
        source_entries = []
        for result in search_results:
            filename = result.metadata.get("filename", "unknown source")
            chunk_index = result.metadata.get("chunk_index")
            snippet = result.metadata.get("text", "").replace("\n", " ")
            if len(snippet) > 300:
                snippet = snippet[:300].rstrip() + "..."
            source_entries.append(
                f"- {filename} [chunk {chunk_index}] (score={result.score:.4f}): {snippet}"
            )

        sources_text = "\n".join(source_entries)

        return (
            "You are a conversational assistant. Use the retrieved document chunks to answer the question. "
            "Preserve user context and session history. If the user asks to book an interview, extract booking details."\
            f"\n\nConversation history:\n{history_text}\n\nRetrieved content:\n{sources_text}\n\nQuestion:\n{query}"
        )

    async def generate(self, prompt: str) -> str:
        return await asyncio.to_thread(self._generate_sync, prompt)

    def _generate_sync(self, prompt: str) -> str:
        response = genai_client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=512,
            ),
        )

        candidate = response.candidates[0] if response.candidates else None
        if not candidate or not candidate.content or not candidate.content.parts:
            return ""

        part = candidate.content.parts[0]
        return (part.text or "").strip()
