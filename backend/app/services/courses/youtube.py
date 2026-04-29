"""
YouTube Data API v3 provider for course recommendations.

Searches for videos matching a career + skills query, returning up to
MAX_RESULTS candidate dicts.  Returns an empty list when the API key is
not configured rather than raising — the aggregator handles graceful
degradation.
"""
from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
_MAX_RESULTS = 10

# Only fetch medium/long videos — short clips are usually not tutorial content
_VIDEO_DURATION = "medium"  # 4–20 min; "long" = 20+ min


async def search_courses(career_name: str, gap_skills: list[str]) -> list[dict]:
    """
    Search YouTube for tutorial/course content relevant to *career_name* and
    the first few *gap_skills*.

    Returns a list of candidate dicts with keys:
        title, url, provider, thumbnail, channel, description

    Returns [] if YOUTUBE_API_KEY is not set or on any API error.
    """
    if not settings.youtube_api_key:
        logger.info("youtube: YOUTUBE_API_KEY not set — skipping")
        return []

    # Use the top 3 gap skills in the query to keep it focused
    skill_fragment = ", ".join(gap_skills[:3]) if gap_skills else ""
    query = f"{career_name} tutorial course {skill_fragment}".strip()

    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": _MAX_RESULTS,
        "videoDuration": _VIDEO_DURATION,
        "relevanceLanguage": "en",
        "key": settings.youtube_api_key,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(_SEARCH_URL, params=params)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning("youtube: API error %d — %s", exc.response.status_code, exc.response.text[:200])
        return []
    except httpx.RequestError as exc:
        logger.warning("youtube: request error — %s", exc)
        return []

    items = resp.json().get("items", [])
    candidates: list[dict] = []

    for item in items:
        vid_id = item.get("id", {}).get("videoId", "")
        if not vid_id:
            continue
        snippet = item.get("snippet", {})
        thumbnails = snippet.get("thumbnails", {})
        thumb = (
            thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url")
        )
        candidates.append(
            {
                "title": snippet.get("title", ""),
                "url": f"https://www.youtube.com/watch?v={vid_id}",
                "provider": "youtube",
                "thumbnail": thumb,
                "channel": snippet.get("channelTitle", ""),
                "description": snippet.get("description", "")[:300],
            }
        )

    logger.info("youtube: fetched %d candidates for '%s'", len(candidates), career_name)
    return candidates
