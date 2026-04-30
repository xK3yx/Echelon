"""
ORM model for chat_messages table.

Stores per-recommendation conversation history with Vantage. Messages
carry their role (user / assistant), the text content, and optional
attachment metadata. Attachment binaries are NOT persisted — only a
short excerpt (e.g. extracted text preview) so the conversation can
reference what was sent without holding files.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

CHAT_ROLES = ("user", "assistant")
ATTACHMENT_KINDS = ("pdf", "docx", "image", "txt")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recommendations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        Enum(*CHAT_ROLES, name="chat_role"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Attachment metadata — kind is one of "pdf"|"docx"|"image"|"txt" or None
    attachment_kind: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachment_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    # First ~500 chars of extracted text for documents, or short caption
    # for images. Not the binary.
    attachment_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
