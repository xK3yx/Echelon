import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

EDUCATION_LEVELS = ("high_school", "diploma", "bachelors", "masters", "phd")


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    skills: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    interests: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    education_level: Mapped[str] = mapped_column(
        Enum(*EDUCATION_LEVELS, name="education_level"), nullable=False
    )
    personality: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    constraints: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
