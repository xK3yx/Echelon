from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    profile_id: UUID
    career_slug: str


class SkillGapResponse(BaseModel):
    skill: str
    difficulty: Literal["easy", "medium", "hard"]


class AnalyzeResponse(BaseModel):
    profile_id: UUID
    career_slug: str
    career_name: str
    skill_gaps: list[SkillGapResponse]
