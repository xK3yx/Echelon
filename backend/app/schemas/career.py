from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

DifficultyLevel = Literal["low", "medium", "high"]
GrowthPotentialLevel = Literal["low", "medium", "high"]
CareerSource = Literal["onet", "manual", "llm_proposed"]


class PersonalityFitSchema(BaseModel):
    openness: int
    conscientiousness: int
    extraversion: int
    agreeableness: int
    neuroticism: int


class CareerRead(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str
    required_skills: list[str]
    optional_skills: list[str]
    personality_fit: PersonalityFitSchema
    difficulty: DifficultyLevel
    growth_potential: GrowthPotentialLevel
    category: str
    source: CareerSource
    onet_soc_code: str | None
    external_url: str | None
    verified: bool
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
