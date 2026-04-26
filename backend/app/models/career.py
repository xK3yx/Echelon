import uuid

from sqlalchemy import Enum, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

DIFFICULTY_LEVELS = ("low", "medium", "high")
GROWTH_POTENTIAL_LEVELS = ("low", "medium", "high")


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
