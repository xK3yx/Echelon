"""
Stage 2.5 — LLM career proposal service.

Triggered only when the best rule-based score is below PROPOSE_THRESHOLD
and the caller set allow_proposed=True.  Returns 0-2 validated career dicts
ready to be persisted to the careers table.

Design notes:
- One Groq call (llama-3.3-70b-versatile, temp 0.5 — needs creativity).
- Retries ONCE with a stricter prompt on validation failure.
- On second failure: logs the error and returns [] — never fails the outer request.
- Deduplicates proposed names against the full set of existing career names
  (case-insensitive) before returning.
"""
from __future__ import annotations

import json
import logging
import uuid

from app.llm import client as groq
from app.llm.prompts import build_proposal_messages, build_proposal_messages_strict
from app.llm.validators import ProposalOutput, ProposedCareerItem
from app.services.matching import ProfileData

logger = logging.getLogger(__name__)


async def run_proposal(
    profile: ProfileData,
    top_career_names: list[str],
    existing_names: set[str],
    model: str,
) -> list[dict]:
    """
    Call the LLM to propose 1–2 novel careers for a low-fit profile.

    Args:
        profile           — the user's profile data
        top_career_names  — names of the top verified matches (context: what NOT to duplicate)
        existing_names    — all active career names in DB (for dedup check)
        model             — Groq model to use (groq_model_ranking)

    Returns a list of dicts ready to be inserted into the careers table as
    source='llm_proposed', verified=False.  May be empty on validation failure
    or if all proposals duplicate existing careers.
    """
    messages = build_proposal_messages(profile, top_career_names)
    content = ""

    try:
        raw = await groq.chat_completion(
            model=model,
            messages=messages,
            temperature=0.5,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
        content = raw["choices"][0]["message"]["content"]
        output = ProposalOutput.model_validate(json.loads(content))
        logger.info("proposal validation: OK (attempt 1)")
    except Exception as exc:
        logger.warning("proposal validation failed (attempt 1): %s", exc)
        # Retry once with stricter prompt at lower temperature
        try:
            strict = build_proposal_messages_strict(
                profile, top_career_names, content
            )
            raw2 = await groq.chat_completion(
                model=model,
                messages=strict,
                temperature=0.2,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )
            content2 = raw2["choices"][0]["message"]["content"]
            output = ProposalOutput.model_validate(json.loads(content2))
            logger.info("proposal validation: OK (attempt 2)")
        except Exception as exc2:
            logger.error("proposal validation failed (attempt 2): %s — skipping proposals", exc2)
            return []

    return _validate_and_build(output.proposed_careers, existing_names)


def _validate_and_build(
    items: list[ProposedCareerItem],
    existing_names: set[str],
) -> list[dict]:
    """
    Apply hard validation rules and build DB-ready dicts.

    Rules (from spec — failures drop the individual item, not the whole batch):
      - name must not duplicate an existing career (case-insensitive)
      - required_skills must not be empty
      - description must be ≥ 50 chars
    """
    existing_lower = {n.lower() for n in existing_names}
    results: list[dict] = []

    for item in items:
        if item.name.lower() in existing_lower:
            logger.warning("proposal dropped: name '%s' duplicates an existing career", item.name)
            continue
        if not item.required_skills:
            logger.warning("proposal dropped: '%s' has empty required_skills", item.name)
            continue
        if len(item.description) < 50:
            logger.warning("proposal dropped: '%s' description too short", item.name)
            continue

        short_id = uuid.uuid4().hex[:8]
        results.append(
            {
                "id": uuid.uuid4(),
                "name": item.name,
                "slug": f"proposed-{short_id}",
                "description": item.description,
                "required_skills": item.required_skills,
                "optional_skills": item.optional_skills,
                "personality_fit": item.personality_fit,
                "difficulty": item.difficulty,
                "growth_potential": item.growth_potential,
                "category": item.category,
                "source": "llm_proposed",
                "verified": False,
                # proposed_for_profile_id is set by the caller (router)
                "rationale": item.rationale,
            }
        )

    return results
