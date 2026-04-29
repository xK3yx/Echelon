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
    is_public: bool = False
    created_at: datetime

    # protected_namespaces=() silences the Pydantic v2 warning about
    # `model_used` colliding with the reserved "model_" namespace.
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class RecommendationPublic(BaseModel):
    """Slimmed-down read schema for public share pages — omits profile_id."""
    id: UUID
    result: dict
    model_used: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
