import io
from typing import Any

import pdfplumber
from fastapi import UploadFile


async def extract_document_text(file: UploadFile) -> str:
    content = await file.read()
    content_stream = io.BytesIO(content)
    if file.content_type == "application/pdf":
        return _extract_pdf_text(content_stream)

    return content.decode("utf-8", errors="ignore")


def _extract_pdf_text(stream: io.BytesIO) -> str:
    text_parts: list[str] = []
    with pdfplumber.open(stream) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)

    return "\n\n".join(text_parts)
