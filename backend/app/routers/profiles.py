import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.career import Career
from app.models.profile import Profile
from app.models.user import User
from app.schemas.matches import MatchesResponse, ScoredCareerRead
from app.schemas.profile import ProfileCreate, ProfileRead
from app.services.matching import CareerData, ProfileData, rank_careers

router = APIRouter(tags=["profiles"])


@router.post("/profiles", response_model=ProfileRead, status_code=201)
async def create_profile(
    body: ProfileCreate,
    db: AsyncSession = Depends(get_db),
) -> Profile:
    user = User(id=uuid.uuid4())
    db.add(user)
    await db.flush()  # persist user before profile FK reference

    profile = Profile(
        id=uuid.uuid4(),
        user_id=user.id,
        skills=body.skills,
        interests=body.interests,
        education_level=body.education_level,
        personality=body.personality.model_dump(),
        constraints=body.constraints,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/profiles/{profile_id}", response_model=ProfileRead)
async def get_profile(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Profile:
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


# Temporary endpoint — replaced by POST /api/recommendations in Phase 4.
# Useful for verifying rule-based scores before wiring the LLM.
@router.get("/profiles/{profile_id}/matches", response_model=MatchesResponse)
async def get_profile_matches(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> MatchesResponse:
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    careers_result = await db.execute(select(Career))
    careers = careers_result.scalars().all()

    profile_data: ProfileData = {
        "skills": profile.skills,
        "interests": profile.interests,
        "personality": profile.personality,
    }
    career_data: list[CareerData] = [
        {
            "id": str(c.id),
            "slug": c.slug,
            "name": c.name,
            "category": c.category,
            "description": c.description,
            "required_skills": c.required_skills,
            "optional_skills": c.optional_skills,
            "personality_fit": c.personality_fit,
        }
        for c in careers
    ]

    scored = rank_careers(profile_data, career_data)
    return MatchesResponse(
        profile_id=profile_id,
        matches=[ScoredCareerRead(**vars(s)) for s in scored],
    )
