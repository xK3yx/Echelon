"""
GET /api/courses/recommend — return ranked course recommendations for a career.

Query parameters:
  career_slug   required  — slug of the career (e.g. "data-scientist")
  career_name   required  — human-readable name (e.g. "Data Scientist")
  skills        optional  — comma-separated gap skills to focus the search

Response shape:
  {
    "courses": [Course, ...],
    "source_note": "<disclaimer about sources>"
  }

Returns an empty courses list (not an error) when no providers are
configured, so the frontend can render a graceful "no courses" state.
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.courses.aggregator import get_courses
from app.services.courses.schemas import Course

router = APIRouter(tags=["courses"])

# Slug must be lowercase-kebab-case.  Validates user-supplied paths
# before they hit the cache lookup or external APIs.
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class CourseRecommendResponse(BaseModel):
    courses: list[Course]
    source_note: str = (
        "YouTube results are full playlists (course series) rather than single "
        "videos so you get a structured learning path. Web results come from "
        "Tavily and may include Udemy, Coursera, edX, freeCodeCamp etc. "
        "Echelon has no partnerships with platforms or creators. "
        "Relevance scores are LLM estimates, not guarantees."
    )


@router.get("/courses/recommend", response_model=CourseRecommendResponse)
async def recommend_courses(
    career_slug: str = Query(
        ...,
        description="Career slug, e.g. 'data-scientist'",
        min_length=1,
        max_length=100,
    ),
    career_name: str = Query(
        ...,
        description="Human-readable career name",
        min_length=1,
        max_length=200,
    ),
    skills: str = Query(
        default="",
        description="Comma-separated gap skills",
        max_length=500,
    ),
    db: AsyncSession = Depends(get_db),
) -> CourseRecommendResponse:
    if not _SLUG_RE.match(career_slug):
        raise HTTPException(
            status_code=422,
            detail="career_slug must be lowercase-kebab-case",
        )

    gap_skills = [s.strip() for s in skills.split(",") if s.strip()] if skills else []

    courses = await get_courses(
        career_slug=career_slug,
        career_name=career_name,
        gap_skills=gap_skills,
        db=db,
    )

    return CourseRecommendResponse(courses=courses)
