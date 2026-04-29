"""
Shared schemas for the course recommendation pipeline.

Course dicts are stored as-is in the CourseCache JSONB column, so every
field must be JSON-serialisable.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class Course(BaseModel):
    title: str
    url: str
    provider: str  # "youtube" or "tavily" (Phase 5b)
    thumbnail: str | None = None
    channel: str
    description: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    rationale: str

    def to_dict(self) -> dict:
        return self.model_dump()


class LLMRankerInput(BaseModel):
    career_name: str
    gap_skills: list[str]
    candidates: list[dict]  # raw dicts from providers, not yet ranked


class RankedCourse(BaseModel):
    title: str
    url: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    rationale: str


class LLMRankerOutput(BaseModel):
    ranked: list[RankedCourse]
