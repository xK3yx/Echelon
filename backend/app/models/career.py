import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Enum, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

DIFFICULTY_LEVELS = ("low", "medium", "high")
GROWTH_POTENTIAL_LEVELS = ("low", "medium", "high")
CAREER_SOURCES = ("onet", "manual", "llm_proposed")


class Career(Base):
    __tablename__ = "careers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    required_skills: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    optional_skills: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    personality_fit: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    difficulty: Mapped[str] = mapped_column(
        Enum(*DIFFICULTY_LEVELS, name="difficulty_level"), nullable=False
    )
    growth_potential: Mapped[str] = mapped_column(
        Enum(*GROWTH_POTENTIAL_LEVELS, name="growth_potential_level"), nullable=False
    )
    category: Mapped[str] = mapped_column(Text, nullable=False)

    # Provenance fields (added in migration 0002)
    source: Mapped[str] = mapped_column(
        Enum(*CAREER_SOURCES, name="career_source"),
        nullable=False,
        default="manual",
        server_default="manual",
    )
    onet_soc_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    proposed_for_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=lambda: datetime.now(UTC),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
