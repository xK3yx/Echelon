import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.llm.client import GroqError
from app.models.career import Career
from app.models.profile import Profile
from app.models.recommendation import Recommendation
from app.schemas.recommendation import RecommendationPublic, RecommendationRead, RecommendationRequest
from app.services.matching import CareerData, ProfileData, rank_careers
from app.services.proposer import run_proposal
from app.services.ranker import run_ranking
from app.services.roadmap import RankedCareerInput, run_gap_roadmap

router = APIRouter(tags=["recommendations"])


def _build_profile_data(profile: Profile) -> ProfileData:
    return {
        "skills": profile.skills,
        "interests": profile.interests,
        "personality": profile.personality,
        "education_level": profile.education_level,
    }


def _build_career_data(career: Career) -> CareerData:
    return {
        "id": str(career.id),
        "slug": career.slug,
        "name": career.name,
        "category": career.category,
        "description": career.description,
        "required_skills": career.required_skills,
        "optional_skills": career.optional_skills,
        "personality_fit": career.personality_fit,
        "difficulty": career.difficulty,
    }


@router.post("/recommendations", response_model=RecommendationRead, status_code=201)
async def create_recommendation(
    body: RecommendationRequest,
    db: AsyncSession = Depends(get_db),
) -> Recommendation:
    # Return cached result unless caller explicitly requests a refresh
    if not body.refresh:
        cached = await db.execute(
            select(Recommendation)
            .where(Recommendation.profile_id == body.profile_id)
            .order_by(Recommendation.created_at.desc())
            .limit(1)
        )
        existing = cached.scalar_one_or_none()
        if existing is not None:
            return existing

    # Load profile
    profile_row = await db.execute(select(Profile).where(Profile.id == body.profile_id))
    profile = profile_row.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Load only verified, non-deleted careers for scoring
    careers_row = await db.execute(
        select(Career).where(Career.verified.is_(True), Career.deleted_at.is_(None))
    )
    careers = list(careers_row.scalars().all())
    if not careers:
        raise HTTPException(
            status_code=409,
            detail="No careers in database. Run `make seed` or `make ingest-onet` first.",
        )

    profile_data = _build_profile_data(profile)
    career_data = [_build_career_data(c) for c in careers]
    career_by_slug = {c.slug: c for c in careers}

    # Stage 1: deterministic rule scoring → top 10
    top10 = rank_careers(profile_data, career_data)
    top_score = top10[0].total_score if top10 else 0.0

    # Stage 2: LLM ranking → top 5 with reasoning
    try:
        ranking_output, scored_top10 = await run_ranking(profile_data, career_data)
    except GroqError as exc:
        raise HTTPException(status_code=502, detail=f"Groq API error: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    scored_by_slug = {s.slug: s for s in scored_top10}

    # Stage 2.5: LLM career proposal (only for low-fit profiles)
    proposed_careers_result: list[dict] = []
    if body.allow_proposed and top_score < settings.propose_threshold:
        existing_names = {c.name for c in careers}
        top5_names = [item.slug for item in ranking_output.ranked_careers]
        top5_display_names = [
            career_by_slug[s].name for s in top5_names if s in career_by_slug
        ]

        proposal_dicts = await run_proposal(
            profile=profile_data,
            top_career_names=top5_display_names,
            existing_names=existing_names,
            model=settings.groq_model_ranking,
        )

        # Persist proposals and build response entries
        for p in proposal_dicts:
            rationale = p.pop("rationale")  # stored in result JSON, not the careers table
            p["proposed_for_profile_id"] = body.profile_id

            career_obj = Career(**p)
            db.add(career_obj)
            await db.flush()  # get the id without committing yet

            proposed_careers_result.append(
                {
                    "id": str(career_obj.id),
                    "name": career_obj.name,
                    "slug": career_obj.slug,
                    "category": career_obj.category,
                    "description": career_obj.description,
                    "source": "llm_proposed",
                    "verified": False,
                    "rationale": rationale,
                }
            )

    # Stage 3: batched gap tagging + roadmap for the 5 ranked careers
    ranked_inputs = [
        RankedCareerInput(
            slug=item.slug,
            name=career_by_slug[item.slug].name,
            category=career_by_slug[item.slug].category,
            required_skills=career_by_slug[item.slug].required_skills,
        )
        for item in ranking_output.ranked_careers
        if item.slug in career_by_slug
    ]

    try:
        gap_roadmap_output = await run_gap_roadmap(profile_data["skills"], ranked_inputs)
    except GroqError as exc:
        raise HTTPException(status_code=502, detail=f"Groq API error: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    gap_roadmap_by_slug = {c.slug: c for c in gap_roadmap_output.careers}

    # Assemble full result — merging ranking + scores + gaps + roadmaps
    result: dict = {
        "ranked_careers": [
            {
                "slug": item.slug,
                "name": career_by_slug[item.slug].name,
                "category": career_by_slug[item.slug].category,
                "source": career_by_slug[item.slug].source,
                "fit_reasoning": item.fit_reasoning,
                "strengths": item.strengths,
                "risks": item.risks,
                "confidence": item.confidence,
                "rule_scores": {
                    "total": scored_by_slug[item.slug].total_score,
                    "skill": scored_by_slug[item.slug].skill_score,
                    "optional": scored_by_slug[item.slug].optional_score,
                    "personality": scored_by_slug[item.slug].personality_score,
                    "interest": scored_by_slug[item.slug].interest_score,
                },
                "skill_gaps": (
                    [g.model_dump() for g in gap_roadmap_by_slug[item.slug].skill_gaps]
                    if item.slug in gap_roadmap_by_slug
                    else []
                ),
                "roadmap": (
                    [r.model_dump() for r in gap_roadmap_by_slug[item.slug].roadmap]
                    if item.slug in gap_roadmap_by_slug
                    else []
                ),
            }
            for item in ranking_output.ranked_careers
            if item.slug in career_by_slug and item.slug in scored_by_slug
        ],
        "proposed_careers": proposed_careers_result,
    }

    rec = Recommendation(
        id=uuid.uuid4(),
        profile_id=body.profile_id,
        result=result,
        model_used=settings.groq_model_ranking,
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return rec


@router.get("/recommendations/{recommendation_id}", response_model=RecommendationRead)
async def get_recommendation(
    recommendation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Recommendation:
    result = await db.execute(select(Recommendation).where(Recommendation.id == recommendation_id))
    rec = result.scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return rec


@router.post("/recommendations/{recommendation_id}/share", response_model=RecommendationRead)
async def share_recommendation(
    recommendation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Recommendation:
    """Mark a recommendation as publicly shareable.  Idempotent."""
    result = await db.execute(select(Recommendation).where(Recommendation.id == recommendation_id))
    rec = result.scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    rec.is_public = True
    await db.commit()
    await db.refresh(rec)
    return rec


@router.get("/recommendations/{recommendation_id}/public", response_model=RecommendationPublic)
async def get_public_recommendation(
    recommendation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Recommendation:
    """Fetch a recommendation without auth — only works when is_public=True."""
    result = await db.execute(select(Recommendation).where(Recommendation.id == recommendation_id))
    rec = result.scalar_one_or_none()
    if rec is None or not rec.is_public:
        raise HTTPException(status_code=404, detail="Recommendation not found or not public")
    return rec
