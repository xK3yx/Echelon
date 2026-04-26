"""
Pydantic schemas that validate LLM JSON output.

All schemas use strict types so that a float where an int is expected (e.g.
confidence: 85.0) triggers a validation error and forces a retry.
"""

from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Ranking (Stage 2)
# ---------------------------------------------------------------------------


class RankedCareerItem(BaseModel):
    slug: str = Field(min_length=1)
    fit_reasoning: str = Field(min_length=20)
    strengths: list[str] = Field(min_length=1, max_length=6)
    risks: list[str] = Field(min_length=1, max_length=5)
    confidence: int = Field(ge=0, le=100)


class RankingOutput(BaseModel):
    """Validated output of the LLM ranking call. Must contain exactly 5 careers."""

    ranked_careers: list[RankedCareerItem] = Field(min_length=5, max_length=5)


# ---------------------------------------------------------------------------
# Gap + Roadmap (Stage 3 — batched for all 5 careers)
# ---------------------------------------------------------------------------


class SkillGapItem(BaseModel):
    skill: str = Field(min_length=1)
    difficulty: Literal["easy", "medium", "hard"]


class RoadmapPhase(BaseModel):
    phase: Literal["Beginner", "Intermediate", "Advanced"]
    skills: list[str] = Field(min_length=1, max_length=8)
    projects: list[str] = Field(min_length=2, max_length=2)
    duration_weeks: int = Field(ge=1, le=52)


class CareerGapRoadmap(BaseModel):
    slug: str = Field(min_length=1)
    skill_gaps: list[SkillGapItem]
    roadmap: list[RoadmapPhase] = Field(min_length=3, max_length=3)


class GapRoadmapOutput(BaseModel):
    """Validated output of the batched gap+roadmap call. One entry per ranked career."""

    careers: list[CareerGapRoadmap] = Field(min_length=1)


# ---------------------------------------------------------------------------
# Analyze (single career, /api/analyze — gap tagging only, no roadmap)
# ---------------------------------------------------------------------------


class AnalyzeOutput(BaseModel):
    """Validated output of the single-career gap-tagging call."""

    slug: str = Field(min_length=1)
    skill_gaps: list[SkillGapItem]
