from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

EducationLevel = Literal["high_school", "diploma", "bachelors", "masters", "phd"]


class PersonalitySchema(BaseModel):
    openness: int = Field(ge=0, le=100)
    conscientiousness: int = Field(ge=0, le=100)
    extraversion: int = Field(ge=0, le=100)
    agreeableness: int = Field(ge=0, le=100)
    neuroticism: int = Field(ge=0, le=100)


class ProfileCreate(BaseModel):
    skills: list[str] = Field(min_length=1)
    interests: list[str] = Field(min_length=1)
    education_level: EducationLevel
    personality: PersonalitySchema
    constraints: dict | None = None


class ProfileRead(BaseModel):
    id: UUID
    user_id: UUID
    skills: list[str]
    interests: list[str]
    education_level: EducationLevel
    personality: PersonalitySchema
    constraints: dict | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
