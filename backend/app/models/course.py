"""
ORM model for the course_cache table.

Stores LLM-ranked course recommendations per career slug.
Each row is keyed on career_slug (unique) and expires after COURSE_CACHE_TTL_DAYS.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CourseCache(Base):
    __tablename__ = "course_cache"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # One cache row per career slug — refreshed when expired
    career_slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    # List of course dicts (title, url, provider, thumbnail, channel, description,
    # relevance_score, rationale) serialised as JSONB
    courses: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
