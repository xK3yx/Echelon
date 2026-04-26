"""
Batched gap-tagging + roadmap generation for the 5 LLM-ranked careers.

One Groq call covers all 5 careers, keeping the total recommendation
pipeline at 2 LLM calls (ranking + this).  Uses llama-3.3-70b-versatile at
temperature 0.2 (more deterministic than ranking) because roadmap content
must be coherent and actionable rather than creative.
"""

import json
import logging

from app.config import settings
from app.llm import client as groq
from app.llm.prompts import build_gap_roadmap_messages, build_gap_roadmap_messages_strict
from app.llm.validators import GapRoadmapOutput
from app.services.gap_analyzer import compute_missing_skills

logger = logging.getLogger(__name__)


class RankedCareerInput:
    """Lightweight container for the data the roadmap prompt needs."""

    __slots__ = ("slug", "name", "category", "required_skills")

    def __init__(
        self,
        slug: str,
        name: str,
        category: str,
        required_skills: list[str],
    ) -> None:
        self.slug = slug
        self.name = name
        self.category = category
        self.required_skills = required_skills


async def run_gap_roadmap(
    user_skills: list[str],
    ranked_careers: list[RankedCareerInput],
) -> GapRoadmapOutput:
    """
    One batched LLM call: difficulty-tag each career's missing skills and
    generate a 3-phase learning roadmap.

    Args:
        user_skills:     flat list of user's current skills
        ranked_careers:  the 5 careers from Stage 2, in rank order

    Returns:
        GapRoadmapOutput with one CareerGapRoadmap per career.

    Raises:
        GroqError — key missing or API error
        ValueError — validation failed on both attempts
    """
    # Pre-compute which skills are missing for each career (deterministic)
    gaps_by_slug: dict[str, list[str]] = {
        c.slug: compute_missing_skills(user_skills, c.required_skills) for c in ranked_careers
    }

    messages = build_gap_roadmap_messages(ranked_careers, gaps_by_slug)
    raw = await groq.chat_completion(
        model=settings.groq_model_ranking,  # llama-3.3-70b-versatile
        messages=messages,
        temperature=0.2,
        max_tokens=4096,
        response_format={"type": "json_object"},
    )
    content = raw["choices"][0]["message"]["content"]

    try:
        output = GapRoadmapOutput.model_validate(json.loads(content))
        logger.info("gap_roadmap validation: OK (attempt 1)")
        return output
    except Exception as exc:
        logger.warning("gap_roadmap validation failed (attempt 1): %s", exc)

    strict = build_gap_roadmap_messages_strict(ranked_careers, gaps_by_slug, content)
    raw2 = await groq.chat_completion(
        model=settings.groq_model_ranking,
        messages=strict,
        temperature=0.1,
        max_tokens=4096,
        response_format={"type": "json_object"},
    )
    content2 = raw2["choices"][0]["message"]["content"]

    try:
        output2 = GapRoadmapOutput.model_validate(json.loads(content2))
        logger.info("gap_roadmap validation: OK (attempt 2)")
        return output2
    except Exception as exc2:
        logger.error("gap_roadmap validation failed (attempt 2): %s", exc2)
        raise ValueError(f"Gap+roadmap generation failed after 2 attempts: {exc2}") from exc2
