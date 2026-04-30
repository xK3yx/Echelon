"""
YouTube Data API v3 provider for course recommendations.

Searches for *playlists* matching a career + skills query.  Playlists are
preferred over single videos because they typically represent full course
series rather than one-off clips, giving users a structured learning path.

Returns an empty list when the API key is not configured rather than
raising — the aggregator handles graceful degradation.
"""
from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
_MAX_RESULTS = 10


async def search_courses(career_name: str, gap_skills: list[str]) -> list[dict]:
    """
    Search YouTube for course/tutorial *playlists* relevant to *career_name*
    and the first few *gap_skills*.

    Returns a list of candidate dicts with keys:
        title, url, provider, thumbnail, channel, description

    Returns [] if YOUTUBE_API_KEY is not set or on any API error.
    """
    if not settings.youtube_api_key:
        logger.info("youtube: YOUTUBE_API_KEY not set — skipping")
        return []

    # Use the top 3 gap skills in the query to keep it focused
    skill_fragment = ", ".join(gap_skills[:3]) if gap_skills else ""
    query = f"{career_name} full course playlist {skill_fragment}".strip()

    params = {
        "part": "snippet",
        "q": query,
        "type": "playlist",
        "maxResults": _MAX_RESULTS,
        # `relevance` is YouTube's quality signal — combines view count,
        # engagement, and freshness.  No videoDuration filter (only valid
        # for type=video).
        "order": "relevance",
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
        playlist_id = item.get("id", {}).get("playlistId", "")
        if not playlist_id:
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
                "url": f"https://www.youtube.com/playlist?list={playlist_id}",
                "provider": "youtube",
                "thumbnail": thumb,
                "channel": snippet.get("channelTitle", ""),
                "description": snippet.get("description", "")[:300],
            }
        )

    logger.info("youtube: fetched %d playlist candidates for '%s'", len(candidates), career_name)
    return candidates
