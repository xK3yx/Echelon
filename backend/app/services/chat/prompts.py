"""
System prompt and message-builder helpers for the Vantage chatbot.

Vantage answers career-related follow-up questions with full context of
the user's profile and their top-5 ranked careers, so users can ask
"why was I recommended this?" or "what should I learn first?" without
having to re-explain their background.
"""
from __future__ import annotations

import json

VANTAGE_SYSTEM_PROMPT = """\
You are Vantage, a career counselling AI assistant inside the Echelon \
career-intelligence app. Your job is to help users understand and explore \
the career recommendations Echelon generated for them.

You have access to the user's profile (skills, interests, personality, \
education) and their top-5 ranked careers including the LLM's fit \
reasoning, strengths, risks, skill gaps, and three-phase learning roadmap.

How to behave:
- Be conversational, warm, and direct. Avoid corporate hedging.
- Stay focused on careers, learning paths, skill development, and \
  professional growth. Politely redirect off-topic questions.
- When asked "why was I recommended X?", reference specific items from \
  the user's profile and the recommendation's strengths/risks/score.
- When asked about learning resources, suggest concrete next steps from \
  the roadmap, plus what to learn first.
- When the user attaches a document or image, acknowledge it and use its \
  content to inform your answer.
- Be honest about limitations: confidence scores are estimates, the \
  career database is curated (not exhaustive), and rankings are not \
  predictions of success.
- Keep responses concise (2–4 paragraphs) unless the user asks for depth.
- Never invent facts about the user's profile or recommendations — if you \
  don't know, say so.
"""


def _format_recommendation(result: dict) -> str:
    """Render the recommendation result dict for the system prompt."""
    ranked = result.get("ranked_careers", [])
    proposed = result.get("proposed_careers", [])
    lines = ["## User's Top 5 Career Matches"]
    for i, career in enumerate(ranked, 1):
        gaps = ", ".join(g["skill"] for g in career.get("skill_gaps", [])[:6])
        lines.append(
            f"\n{i}. {career['name']} (confidence {career['confidence']}%)"
            f"\n   Category: {career['category']}"
            f"\n   Why it fits: {career['fit_reasoning']}"
            f"\n   Strengths: {'; '.join(career.get('strengths', []))}"
            f"\n   Risks: {'; '.join(career.get('risks', []))}"
            f"\n   Skill gaps to close: {gaps or 'none'}"
        )
    if proposed:
        lines.append("\n## AI-proposed (speculative) careers")
        for c in proposed:
            lines.append(f"- {c['name']} — {c.get('rationale', '')}")
    return "\n".join(lines)


def _format_profile(profile: dict) -> str:
    """Render the user profile dict for the system prompt."""
    p = profile.get("personality", {})
    return (
        "## User Profile\n"
        f"Skills: {', '.join(profile.get('skills', [])) or 'none listed'}\n"
        f"Interests: {', '.join(profile.get('interests', [])) or 'none listed'}\n"
        f"Education level: {profile.get('education_level', 'unspecified')}\n"
        f"Personality (Big Five 0-100): "
        f"O={p.get('openness', '?')} "
        f"C={p.get('conscientiousness', '?')} "
        f"E={p.get('extraversion', '?')} "
        f"A={p.get('agreeableness', '?')} "
        f"N={p.get('neuroticism', '?')}"
    )


def build_context_block(profile: dict, recommendation_result: dict) -> str:
    """
    Build the persistent context block that prepends every Vantage
    conversation. Combines profile + recommendation result.
    """
    return (
        f"{_format_profile(profile)}\n\n{_format_recommendation(recommendation_result)}"
    )


def build_attachment_note(
    kind: str | None,
    name: str | None,
    excerpt: str | None,
) -> str:
    """
    Build the attachment indicator that prepends the user's message text
    when a file was uploaded.
    """
    if not kind:
        return ""
    if kind == "image":
        return f"[The user attached an image: {name or 'image'}]\n\n"
    return (
        f"[The user attached a {kind.upper()} file: {name or 'document'}.\n"
        f"Extracted content:\n{excerpt or '(empty)'}\n]\n\n"
    )
