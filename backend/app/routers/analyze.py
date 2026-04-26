from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.llm.client import GroqError
from app.models.career import Career
from app.models.profile import Profile
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse, SkillGapResponse
from app.services.gap_analyzer import compute_missing_skills, run_analyze

router = APIRouter(tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_gap(
    body: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
) -> AnalyzeResponse:
    profile_row = await db.execute(select(Profile).where(Profile.id == body.profile_id))
    profile = profile_row.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    career_row = await db.execute(select(Career).where(Career.slug == body.career_slug))
    career = career_row.scalar_one_or_none()
    if career is None:
        raise HTTPException(status_code=404, detail="Career not found")

    missing = compute_missing_skills(profile.skills, career.required_skills)

    try:
        result = await run_analyze(career.slug, career.name, missing)
    except GroqError as exc:
        raise HTTPException(status_code=502, detail=f"Groq API error: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return AnalyzeResponse(
        profile_id=body.profile_id,
        career_slug=career.slug,
        career_name=career.name,
        skill_gaps=[SkillGapResponse(**g.model_dump()) for g in result.skill_gaps],
    )
