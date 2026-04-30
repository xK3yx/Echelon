"""
Vantage chatbot endpoints — career conversation tied to a recommendation.

  GET  /api/chat/{recommendation_id}/messages
       List all chat messages in chronological order.

  POST /api/chat/{recommendation_id}/messages
       Multipart form: text field 'message' (required) + optional 'file'.
       Returns the assistant's reply as a single ChatMessageRead.

Auth model: same as recommendations — possession of the UUID is enough.
The owner shares the URL/page with whoever they want; no account needed.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.limiter import limiter
from app.llm.client import GroqError
from app.services.chat.attachments import AttachmentError, process as process_attachment
from app.services.chat.service import load_history, send_message

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

# Pydantic v2 read schema mirrors ChatMessage
class ChatMessageRead(BaseModel):
    id: uuid.UUID
    recommendation_id: uuid.UUID
    role: str
    content: str
    attachment_kind: str | None
    attachment_name: str | None
    attachment_excerpt: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessageRead]


@router.get(
    "/chat/{recommendation_id}/messages",
    response_model=ChatHistoryResponse,
)
async def get_chat_history(
    recommendation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ChatHistoryResponse:
    history = await load_history(recommendation_id, db)
    return ChatHistoryResponse(
        messages=[ChatMessageRead.model_validate(m) for m in history]
    )


def _chat_error(reason: str, status: int = 400) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"code": "CHAT_ERROR", "message": reason, "details": {}},
    )


@router.post(
    "/chat/{recommendation_id}/messages",
    response_model=ChatMessageRead,
)
@limiter.limit("30/hour")
async def post_chat_message(
    request: Request,
    recommendation_id: uuid.UUID,
    message: Annotated[str, Form(description="The user's message text")],
    file: Annotated[
        UploadFile | None,
        File(description="Optional attachment — PDF, DOCX, TXT, or image"),
    ] = None,
    db: AsyncSession = Depends(get_db),
) -> ChatMessageRead:
    if not message.strip() and file is None:
        raise _chat_error("Message text or an attachment is required.")

    attachment = None
    if file is not None:
        file_bytes = await file.read()
        if file_bytes:  # ignore empty stub uploads
            try:
                attachment = process_attachment(file_bytes, file.filename or "attachment")
            except AttachmentError as exc:
                raise _chat_error(str(exc))

    try:
        assistant = await send_message(
            recommendation_id=recommendation_id,
            user_text=message,
            attachment=attachment,
            db=db,
        )
    except ValueError as exc:
        if str(exc) == "recommendation_not_found":
            raise HTTPException(status_code=404, detail="Recommendation not found")
        raise
    except GroqError as exc:
        raise HTTPException(
            status_code=502, detail=f"LLM error: {exc}"
        ) from exc

    return ChatMessageRead.model_validate(assistant)
