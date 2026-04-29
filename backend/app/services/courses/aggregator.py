"""
Course recommendation aggregator.

Orchestrates:
  1. Cache lookup (CourseCache by career_slug)
  2. Parallel provider fetch (YouTube + Tavily) with URL-level dedup
  3. LLM ranking
  4. Cache write

Returns an empty list gracefully when no providers are configured (both
API keys absent) — the frontend renders a "no courses available" state.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.course import CourseCache
from app.services.courses import tavily, youtube
from app.services.courses.ranker import rank_courses
from app.services.courses.schemas import Course

logger = logging.getLogger(__name__)


def _dedup(candidates: list[dict]) -> list[dict]:
    """Remove duplicate URLs, keeping first occurrence (YouTube takes priority)."""
    seen: set[str] = set()
    out: list[dict] = []
    for c in candidates:
        if c["url"] not in seen:
            seen.add(c["url"])
            out.append(c)
    return out


async def get_courses(
    career_slug: str,
    career_name: str,
    gap_skills: list[str],
    db: AsyncSession,
) -> list[Course]:
    """
    Return ranked course recommendations for *career_slug*.

    Checks the cache first.  On a miss, fetches from YouTube and Tavily in
    parallel, deduplicates by URL, ranks via LLM, stores in cache, and
    returns the result.
    """
    # ── 1. Cache lookup ────────────────────────────────────────────────────
    now = datetime.now(UTC)
    cached_row = await db.execute(
        select(CourseCache).where(
            CourseCache.career_slug == career_slug,
            CourseCache.expires_at > now,
        )
    )
    cached = cached_row.scalar_one_or_none()
    if cached is not None:
        logger.info("course_cache: HIT for slug=%s", career_slug)
        return [Course(**c) for c in cached.courses]

    logger.info("course_cache: MISS for slug=%s — fetching from providers", career_slug)

    # ── 2. Parallel provider fetch ─────────────────────────────────────────
    yt_results, tv_results = await asyncio.gather(
        youtube.search_courses(career_name, gap_skills),
        tavily.search_courses(career_name, gap_skills),
        return_exceptions=True,
    )

    # gather with return_exceptions=True — convert any unexpected exceptions to []
    if isinstance(yt_results, BaseException):
        logger.warning("course_aggregator: youtube raised %s", yt_results)
        yt_results = []
    if isinstance(tv_results, BaseException):
        logger.warning("course_aggregator: tavily raised %s", tv_results)
        tv_results = []

    # YouTube first so its results survive dedup when both return the same URL
    candidates = _dedup(list(yt_results) + list(tv_results))

    if not candidates:
        logger.info("course_aggregator: no candidates from any provider for slug=%s", career_slug)
        return []

    # ── 3. LLM ranking ────────────────────────────────────────────────────
    provider_map = {c["url"]: c for c in candidates}
    courses = await rank_courses(career_name, gap_skills, candidates, provider_map)

    # ── 4. Cache write ─────────────────────────────────────────────────────
    expires_at = now + timedelta(days=settings.course_cache_ttl_days)
    course_dicts = [c.to_dict() for c in courses]

    existing = await db.execute(
        select(CourseCache).where(CourseCache.career_slug == career_slug)
    )
    row = existing.scalar_one_or_none()

    if row is None:
        db.add(
            CourseCache(
                career_slug=career_slug,
                courses=course_dicts,
                fetched_at=now,
                expires_at=expires_at,
            )
        )
    else:
        row.courses = course_dicts
        row.fetched_at = now
        row.expires_at = expires_at

    await db.commit()
    logger.info(
        "course_cache: stored %d courses for slug=%s, expires=%s",
        len(courses),
        career_slug,
        expires_at.date(),
    )
    return courses
