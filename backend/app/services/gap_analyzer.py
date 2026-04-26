"""
Skill gap analysis — two responsibilities:

1. compute_missing_skills() — purely deterministic, no LLM.
   Called by both the recommendations pipeline and /api/analyze.

2. run_analyze() — single LLM call (llama-3.1-8b-instant) that tags the
   missing skills with easy/medium/hard difficulty.  Used only by the
   /api/analyze endpoint.  The lighter model is appropriate here because
   this step is straightforward extraction/classification, not reasoning.
"""

import json
import logging

from app.config import settings
from app.llm import client as groq
from app.llm.prompts import build_analyze_messages, build_analyze_messages_strict
from app.llm.validators import AnalyzeOutput

logger = logging.getLogger(__name__)


def compute_missing_skills(
    user_skills: list[str],
    required_skills: list[str],
) -> list[str]:
    """
    Return the subset of required_skills the user does not possess.

    Order is preserved (matches the order in required_skills, which reflects
    the career dataset's implicit priority).  Comparison is case-insensitive.
    """
    user_lower = {s.lower() for s in user_skills}
    return [s for s in required_skills if s.lower() not in user_lower]


async def run_analyze(
    career_slug: str,
    career_name: str,
    missing_skills: list[str],
) -> AnalyzeOutput:
    """
    Tag each missing skill with a learning-difficulty estimate.

    Uses llama-3.1-8b-instant (extraction task — no deep reasoning needed).
    Retries once with a stricter prompt on validation failure.

    Returns AnalyzeOutput with skill_gaps list.
    Raises GroqError or ValueError on failure.
    """
    if not missing_skills:
        return AnalyzeOutput(slug=career_slug, skill_gaps=[])

    messages = build_analyze_messages(career_slug, career_name, missing_skills)
    raw = await groq.chat_completion(
        # llama-3.1-8b-instant: adequate for classification; faster and cheaper
        model=settings.groq_model_extraction,
        messages=messages,
        temperature=0.2,
        max_tokens=512,
        response_format={"type": "json_object"},
    )
    content = raw["choices"][0]["message"]["content"]

    try:
        output = AnalyzeOutput.model_validate(json.loads(content))
        logger.info("analyze validation: OK (attempt 1) | career=%s", career_slug)
        return output
    except Exception as exc:
        logger.warning("analyze validation failed (attempt 1) | career=%s | %s", career_slug, exc)

    strict = build_analyze_messages_strict(career_slug, career_name, missing_skills, content)
    raw2 = await groq.chat_completion(
        model=settings.groq_model_extraction,
        messages=strict,
        temperature=0.1,
        max_tokens=512,
        response_format={"type": "json_object"},
    )
    content2 = raw2["choices"][0]["message"]["content"]

    try:
        output2 = AnalyzeOutput.model_validate(json.loads(content2))
        logger.info("analyze validation: OK (attempt 2) | career=%s", career_slug)
        return output2
    except Exception as exc2:
        logger.error("analyze validation failed (attempt 2) | career=%s | %s", career_slug, exc2)
        msg = f"Gap analysis failed after 2 attempts for '{career_slug}': {exc2}"
        raise ValueError(msg) from exc2
