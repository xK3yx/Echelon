from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RecommendationRequest(BaseModel):
    profile_id: UUID
    refresh: bool = False
    allow_proposed: bool = True


class RecommendationRead(BaseModel):
    id: UUID
    profile_id: UUID
    result: dict
    model_used: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
