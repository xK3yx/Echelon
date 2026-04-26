"""
Recommendation pipeline — Stage 1 (rule scoring) + Stage 2 (LLM re-ranking).

Groq is called with JSON mode enabled.  Output is validated against
RankingOutput; on failure the call is retried once with a stricter prompt
and lower temperature.  If both attempts fail, ValueError is raised so the
router can return a structured 502 to the client.
"""

import json
import logging

from app.config import settings
from app.llm import client as groq
from app.llm.prompts import build_ranking_messages, build_ranking_messages_strict
from app.llm.validators import RankingOutput
from app.services.matching import CareerData, ProfileData, ScoredCareer, rank_careers

logger = logging.getLogger(__name__)


async def run_ranking(
    profile: ProfileData,
    all_careers: list[CareerData],
) -> tuple[RankingOutput, list[ScoredCareer]]:
    """
    Run the two-stage recommendation pipeline.

    Stage 1: deterministic rule-based scoring → top 10 candidates
    Stage 2: Groq LLM re-ranking → top 5 with reasoning

    Returns:
        (RankingOutput, top10_scored) so callers can cross-reference rule
        scores by slug when building the stored result.

    Raises:
        GroqError — API key missing or Groq HTTP error
        ValueError — LLM output failed validation on both attempts
    """
    # Stage 1 — rule-based, deterministic
    top10 = rank_careers(profile, all_careers)
    logger.info("Stage 1 complete | top10 slugs: %s", [s.slug for s in top10])

    # Stage 2 — LLM re-ranking (attempt 1)
    messages = build_ranking_messages(profile, top10, all_careers)
    raw = await groq.chat_completion(
        model=settings.groq_model_ranking,
        messages=messages,
        temperature=0.3,
        max_tokens=2048,
        response_format={"type": "json_object"},
    )
    content = raw["choices"][0]["message"]["content"]

    try:
        output = RankingOutput.model_validate(json.loads(content))
        logger.info("Stage 2 validation: OK (attempt 1)")
        return output, top10
    except Exception as exc:
        logger.warning("Stage 2 validation failed (attempt 1): %s", exc)

    # Retry with stricter prompt and lower temperature
    strict_messages = build_ranking_messages_strict(profile, top10, all_careers, content)
    raw2 = await groq.chat_completion(
        model=settings.groq_model_ranking,
        messages=strict_messages,
        temperature=0.1,
        max_tokens=2048,
        response_format={"type": "json_object"},
    )
    content2 = raw2["choices"][0]["message"]["content"]

    try:
        output2 = RankingOutput.model_validate(json.loads(content2))
        logger.info("Stage 2 validation: OK (attempt 2)")
        return output2, top10
    except Exception as exc2:
        logger.error("Stage 2 validation failed (attempt 2): %s", exc2)
        raise ValueError(f"LLM ranking failed after 2 attempts: {exc2}") from exc2
