"""
Tavily Search API provider for course recommendations.

Searches the web for tutorial/course content relevant to a career + skill
gaps.  Returns an empty list when the API key is not configured or on any
API error — the aggregator handles graceful degradation.
"""
from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://api.tavily.com/search"
_MAX_RESULTS = 8

# Preferred domains boost signal-to-noise vs generic web results
_INCLUDE_DOMAINS = [
    "udemy.com",
    "coursera.org",
    "edx.org",
    "pluralsight.com",
    "linkedin.com/learning",
    "freecodecamp.org",
    "youtube.com",
    "skillshare.com",
    "datacamp.com",
    "kaggle.com",
]


async def search_courses(career_name: str, gap_skills: list[str]) -> list[dict]:
    """
    Search Tavily for course/tutorial content relevant to *career_name* and
    the first few *gap_skills*.

    Returns a list of candidate dicts with keys:
        title, url, provider, thumbnail, channel, description

    Returns [] if TAVILY_API_KEY is not set or on any API error.
    """
    if not settings.tavily_api_key:
        logger.info("tavily: TAVILY_API_KEY not set — skipping")
        return []

    skill_fragment = ", ".join(gap_skills[:3]) if gap_skills else ""
    query = f"{career_name} online course tutorial {skill_fragment}".strip()

    payload = {
        "api_key": settings.tavily_api_key,
        "query": query,
        "search_depth": "basic",
        "max_results": _MAX_RESULTS,
        "include_domains": _INCLUDE_DOMAINS,
        "include_answer": False,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(_SEARCH_URL, json=payload)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "tavily: API error %d — %s",
            exc.response.status_code,
            exc.response.text[:200],
        )
        return []
    except httpx.RequestError as exc:
        logger.warning("tavily: request error — %s", exc)
        return []

    results = resp.json().get("results", [])
    candidates: list[dict] = []

    for item in results:
        url = item.get("url", "")
        if not url:
            continue
        # Derive a short channel/source label from the domain
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.lstrip("www.")
        except Exception:
            domain = "web"

        candidates.append(
            {
                "title": item.get("title", ""),
                "url": url,
                "provider": "tavily",
                "thumbnail": None,  # Tavily search results don't include thumbnails
                "channel": domain,
                "description": (item.get("content") or item.get("snippet") or "")[:300],
            }
        )

    logger.info("tavily: fetched %d candidates for '%s'", len(candidates), career_name)
    return candidates
