"""
Pydantic schemas for the resume parsing service.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

EducationLevel = Literal["high_school", "diploma", "bachelors", "masters", "phd"]


class LLMResumeOutput(BaseModel):
    """Schema the LLM must return — validated before use."""

    is_resume: bool
    reason: str | None = None  # present only when is_resume=False
    name: str | None = None
    email: str | None = None
    skills: list[str] = Field(default_factory=list)
    education_level: EducationLevel | None = None
    interests: list[str] = Field(default_factory=list)
    years_experience: int | None = None
    summary: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class ExtractedProfile(BaseModel):
    """Structured profile data returned to the frontend for form prefill."""

    name: str | None = None
    email: str | None = None
    skills: list[str] = Field(default_factory=list)
    education_level: EducationLevel | None = None
    interests: list[str] = Field(default_factory=list)
    years_experience: int | None = None
    summary: str | None = None


class ResumeParseResponse(BaseModel):
    """Response body for POST /api/resume/parse."""

    extracted: ExtractedProfile
    confidence: float = Field(ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
