from pydantic import BaseModel, Field, model_validator

from app.schemas.career import (
    CareerSource,
    DifficultyLevel,
    GrowthPotentialLevel,
    PersonalityFitSchema,
)


class CareerCreate(BaseModel):
    name: str = Field(..., min_length=2)
    slug: str = Field(..., min_length=2, pattern=r"^[a-z0-9-]+$")
    description: str = Field(..., min_length=10)
    required_skills: list[str] = Field(..., min_length=1)
    optional_skills: list[str] = []
    personality_fit: PersonalityFitSchema
    difficulty: DifficultyLevel
    growth_potential: GrowthPotentialLevel
    category: str = Field(..., min_length=2)
    source: CareerSource = "manual"
    onet_soc_code: str | None = None
    external_url: str | None = None

    @model_validator(mode="after")
    def proposed_must_not_be_created_directly(self) -> "CareerCreate":
        if self.source == "llm_proposed":
            raise ValueError(
                "source='llm_proposed' is reserved for the AI proposal flow; "
                "use 'manual' for admin-created careers."
            )
        return self


class CareerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2)
    slug: str | None = Field(default=None, min_length=2, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(default=None, min_length=10)
    required_skills: list[str] | None = None
    optional_skills: list[str] | None = None
    personality_fit: PersonalityFitSchema | None = None
    difficulty: DifficultyLevel | None = None
    growth_potential: GrowthPotentialLevel | None = None
    category: str | None = None
    external_url: str | None = None
