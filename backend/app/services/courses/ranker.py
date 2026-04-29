"""
LLM-based course ranker.

Takes a list of raw candidate dicts from providers and asks the LLM to
select and score the top 5 most relevant for a given career + skill gaps.

Uses groq_model_extraction (small model) — this is a straightforward
selection/scoring task, not deep reasoning.
"""
from __future__ import annotations

import json
import logging

from app.config import settings
from app.llm import client as groq
from app.services.courses.schemas import Course, LLMRankerOutput

logger = logging.getLogger(__name__)

_SYSTEM = """\
You are a career learning advisor. Given a target career, the learner's skill gaps, \
and a list of candidate tutorial videos, select the best 5 (or fewer if there are fewer \
candidates) and score each for relevance.

Respond ONLY with valid JSON in this exact shape:
{
  "ranked": [
    {
      "title": "<exact title from the candidate list>",
      "url": "<exact url from the candidate list>",
      "relevance_score": <0.0–1.0>,
      "rationale": "<one sentence explaining why this is useful for the learner>"
    }
  ]
}

Rules:
- Only include candidates from the provided list — never invent new ones.
- relevance_score 1.0 = perfect match for the career and skill gaps; 0.0 = irrelevant.
- Order by relevance_score descending.
- Maximum 5 items.
- No markdown fences, no explanation outside the JSON.\
"""


def _build_messages(
    career_name: str,
    gap_skills: list[str],
    candidates: list[dict],
) -> list[dict]:
    candidate_lines = "\n".join(
        f"{i + 1}. title={c['title']!r} | url={c['url']!r} | "
        f"channel={c['channel']!r} | desc={c['description'][:120]!r}"
        for i, c in enumerate(candidates)
    )
    user_content = (
        f"Career: {career_name}\n"
        f"Skill gaps: {', '.join(gap_skills) if gap_skills else 'general'}\n\n"
        f"Candidates:\n{candidate_lines}"
    )
    return [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": user_content},
    ]


async def rank_courses(
    career_name: str,
    gap_skills: list[str],
    candidates: list[dict],
    provider_map: dict[str, dict],
) -> list[Course]:
    """
    LLM-rank *candidates* and return up to 5 Course objects.

    *provider_map* maps url → full candidate dict so we can merge the
    LLM selection back to the original data (thumbnail, channel, etc.).

    Falls back to returning the first 5 candidates verbatim (score=0.5)
    if the LLM call fails, so the endpoint never returns an empty list
    when candidates exist.
    """
    if not candidates:
        return []

    messages = _build_messages(career_name, gap_skills, candidates)

    try:
        raw = await groq.chat_completion(
            model=settings.groq_model_extraction,
            messages=messages,
            temperature=0.2,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
        content = raw["choices"][0]["message"]["content"]
        output = LLMRankerOutput.model_validate(json.loads(content))
    except Exception as exc:
        logger.warning("course_ranker: LLM failed (%s) — using unranked fallback", exc)
        # Fallback: return first 5 with neutral score
        return [
            Course(
                title=c["title"],
                url=c["url"],
                provider=c["provider"],
                thumbnail=c.get("thumbnail"),
                channel=c["channel"],
                description=c["description"],
                relevance_score=0.5,
                rationale="Ranking unavailable — shown in default order.",
            )
            for c in candidates[:5]
        ]

    courses: list[Course] = []
    for ranked in output.ranked:
        orig = provider_map.get(ranked.url)
        if orig is None:
            # LLM hallucinated a URL — skip
            logger.warning("course_ranker: LLM returned unknown url %r", ranked.url)
            continue
        courses.append(
            Course(
                title=ranked.title or orig["title"],
                url=ranked.url,
                provider=orig["provider"],
                thumbnail=orig.get("thumbnail"),
                channel=orig["channel"],
                description=orig["description"],
                relevance_score=ranked.relevance_score,
                rationale=ranked.rationale,
            )
        )

    logger.info(
        "course_ranker: ranked %d courses for '%s'", len(courses), career_name
    )
    return courses
