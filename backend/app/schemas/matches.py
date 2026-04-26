from uuid import UUID

from pydantic import BaseModel


class ScoredCareerRead(BaseModel):
    career_id: str
    slug: str
    name: str
    category: str
    total_score: float
    skill_score: float
    optional_score: float
    personality_score: float
    interest_score: float


class MatchesResponse(BaseModel):
    profile_id: UUID
    matches: list[ScoredCareerRead]
