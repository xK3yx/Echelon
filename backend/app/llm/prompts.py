"""
All LLM prompt templates for Echelon v2.

Each public symbol is a constant or builder function.
Builder functions produce the `messages` list expected by chat_completion().
Docstrings describe inputs and the expected JSON output shape.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.matching import CareerData, ProfileData, ScoredCareer

if TYPE_CHECKING:
    from app.services.roadmap import RankedCareerInput

# ---------------------------------------------------------------------------
# Ranking — Stage 2 of the recommendation pipeline
# Used in: services/ranker.py
# Temperature: 0.3   Max tokens: 2048
# ---------------------------------------------------------------------------

RANKING_SYSTEM_PROMPT = """\
You are a career counseling assistant. You will receive a user profile and a \
list of 10 candidate careers pre-scored by a deterministic matching engine.

Your task: select the 5 best-fitting careers for this specific user, ordered \
best-fit first, and explain your reasoning in concrete terms.

Return ONLY a valid JSON object with this exact schema — no markdown, \
no code fences, no text outside the JSON:

{
  "ranked_careers": [
    {
      "slug": "<one of the slugs from the candidate list>",
      "fit_reasoning": "<2-3 sentences referencing the user's specific skills, personality, or interests>",
      "strengths": ["<why this career suits this user>", "..."],
      "risks": ["<potential challenge for this user>", "..."],
      "confidence": <integer 0-100>
    }
  ]
}

Rules:
- ranked_careers must contain EXACTLY 5 objects
- slug must be copied verbatim from the candidate list — do not invent slugs
- fit_reasoning must be specific to this user, not generic career advice
- strengths: 2–4 items
- risks: 1–3 items
- confidence: 0 = very uncertain, 100 = extremely confident

Example output (abbreviated):
{
  "ranked_careers": [
    {
      "slug": "data-scientist",
      "fit_reasoning": "The user's Python and Statistics skills directly cover the core requirements, and their high openness score (80) aligns well with the exploratory nature of data science work.",
      "strengths": ["Strong Python and SQL foundation", "High openness drives curiosity in unknown datasets"],
      "risks": ["Limited experience with deep learning may slow progress on advanced projects"],
      "confidence": 88
    }
  ]
}
"""

RANKING_SYSTEM_PROMPT_STRICT = """\
You are a career counseling assistant. Your previous response did not match \
the required schema. You MUST fix it now.

Required schema — return ONLY this JSON, nothing else:

{
  "ranked_careers": [
    {
      "slug": "<verbatim from candidate list>",
      "fit_reasoning": "<2-3 sentences>",
      "strengths": ["...", "..."],
      "risks": ["..."],
      "confidence": <0-100 integer>
    }
  ]
}

CRITICAL REQUIREMENTS (non-negotiable):
1. ranked_careers must have EXACTLY 5 items — not 4, not 6, exactly 5
2. Every slug must appear in the candidate list provided
3. confidence must be an integer, not a float or string
4. No markdown, no code fences, no text outside the JSON object
"""


def _format_profile(profile: ProfileData) -> str:
    p = profile["personality"]
    lines = [
        "## User Profile",
        f"Skills: {', '.join(profile['skills']) or 'None listed'}",
        f"Interests: {', '.join(profile['interests']) or 'None listed'}",
        "Personality (Big Five, scale 0–100):",
        f"  Openness to experience: {p['openness']}",
        f"  Conscientiousness:      {p['conscientiousness']}",
        f"  Extraversion:           {p['extraversion']}",
        f"  Agreeableness:          {p['agreeableness']}",
        f"  Neuroticism:            {p['neuroticism']}",
    ]
    return "\n".join(lines)


def _format_candidates(top10: list[ScoredCareer], all_careers: list[CareerData]) -> str:
    career_map = {c["slug"]: c for c in all_careers}
    lines = ["## Candidate Careers (rule-based rank, best first)"]
    for i, scored in enumerate(top10, 1):
        c = career_map.get(scored.slug, {})
        req = ", ".join(c.get("required_skills", []))
        opt = ", ".join(c.get("optional_skills", []))
        lines += [
            f"\n{i}. slug: {scored.slug}",
            f"   Name: {scored.name}",
            f"   Category: {scored.category}",
            f"   Required skills: {req}",
            f"   Optional skills: {opt}",
            f"   Rule scores — total: {scored.total_score:.3f} | "
            f"skill: {scored.skill_score:.3f} | "
            f"personality: {scored.personality_score:.3f} | "
            f"interest: {scored.interest_score:.3f}",
        ]
    return "\n".join(lines)


def build_ranking_messages(
    profile: ProfileData,
    top10: list[ScoredCareer],
    all_careers: list[CareerData],
) -> list[dict]:
    """
    Build the messages list for the LLM ranking call.

    Inputs:
      profile    — the user's profile data dict
      top10      — scored careers from Stage 1 (up to 10)
      all_careers — full career dataset (used to look up metadata by slug)

    Expected output: JSON matching RankingOutput schema (ranked_careers, 5 items).
    """
    user_content = "\n\n".join(
        [
            _format_profile(profile),
            _format_candidates(top10, all_careers),
            "## Task\nSelect and rank the 5 best-fitting careers for this user. "
            "Return the JSON object described in the system prompt.",
        ]
    )
    return [
        {"role": "system", "content": RANKING_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def build_ranking_messages_strict(
    profile: ProfileData,
    top10: list[ScoredCareer],
    all_careers: list[CareerData],
    previous_response: str,
) -> list[dict]:
    """
    Stricter retry prompt used when the first ranking attempt fails validation.

    Includes the previous (invalid) response so the model can see what went wrong.
    Temperature should be lowered to 0.1 for this call.
    """
    user_content = "\n\n".join(
        [
            _format_profile(profile),
            _format_candidates(top10, all_careers),
            f"## Your Previous (Invalid) Response\n```\n{previous_response[:1000]}\n```",
            "## Task\nFix the above response so it matches the required schema exactly. "
            "Return ONLY the corrected JSON. ranked_careers must have EXACTLY 5 items.",
        ]
    )
    return [
        {"role": "system", "content": RANKING_SYSTEM_PROMPT_STRICT},
        {"role": "user", "content": user_content},
    ]


# ---------------------------------------------------------------------------
# Gap + Roadmap — Stage 3 of the recommendation pipeline (batched, all 5)
# Used in: services/roadmap.py
# Temperature: 0.2   Max tokens: 4096   Model: groq_model_ranking
# ---------------------------------------------------------------------------

GAP_ROADMAP_SYSTEM_PROMPT = """\
You are a career development assistant. For each career provided you will:
1. Tag each missing skill with a learning difficulty (easy / medium / hard).
2. Write a 3-phase learning roadmap (Beginner → Intermediate → Advanced).

Return ONLY a valid JSON object — no markdown, no code fences, no extra text:

{
  "careers": [
    {
      "slug": "<verbatim from input>",
      "skill_gaps": [
        {"skill": "<skill name>", "difficulty": "easy|medium|hard"}
      ],
      "roadmap": [
        {
          "phase": "Beginner",
          "skills": ["skill to learn", "..."],
          "projects": ["Specific project idea 1", "Specific project idea 2"],
          "duration_weeks": 8
        },
        {
          "phase": "Intermediate",
          "skills": ["..."],
          "projects": ["...", "..."],
          "duration_weeks": 12
        },
        {
          "phase": "Advanced",
          "skills": ["..."],
          "projects": ["...", "..."],
          "duration_weeks": 16
        }
      ]
    }
  ]
}

Rules:
- Include ALL career slugs from the input, in the same order.
- skill_gaps: tag every skill from the provided missing_skills list.
  easy   = learnable in days/weeks with adjacent experience
  medium = weeks to months of focused study
  hard   = months to a year or requires deep prior knowledge
- roadmap: EXACTLY 3 phases — Beginner, Intermediate, Advanced in that order.
- projects: EXACTLY 2 items per phase — be specific and buildable (not "build an app").
- skills per phase: 2–6 skills.
- duration_weeks: realistic integers (Beginner 4–12, Intermediate 8–16, Advanced 12–24).
- If skill_gaps is empty for a career, return an empty skill_gaps array [].
"""

GAP_ROADMAP_SYSTEM_PROMPT_STRICT = """\
Your previous response did not match the required schema. Fix it now.

Required JSON structure:
{
  "careers": [
    {
      "slug": "<string>",
      "skill_gaps": [{"skill": "<string>", "difficulty": "easy|medium|hard"}],
      "roadmap": [
        {"phase": "Beginner",      "skills": [...], "projects": ["<str>","<str>"], "duration_weeks": <int>},
        {"phase": "Intermediate",  "skills": [...], "projects": ["<str>","<str>"], "duration_weeks": <int>},
        {"phase": "Advanced",      "skills": [...], "projects": ["<str>","<str>"], "duration_weeks": <int>}
      ]
    }
  ]
}

CRITICAL:
- careers must contain ALL slugs from the input.
- roadmap must have EXACTLY 3 phases: Beginner, Intermediate, Advanced.
- projects must have EXACTLY 2 strings per phase.
- duration_weeks must be an integer (not a string, not a float).
- Return ONLY the JSON. Nothing else.
"""


def _format_gap_roadmap_input(
    ranked_careers: list[RankedCareerInput],
    gaps_by_slug: dict[str, list[str]],
) -> str:
    lines = ["## Careers to Analyse"]
    for i, c in enumerate(ranked_careers, 1):
        missing = gaps_by_slug.get(c.slug, [])
        lines += [
            f"\n{i}. slug: {c.slug}",
            f"   Name: {c.name}  |  Category: {c.category}",
            f"   Missing required skills: {', '.join(missing) if missing else 'none'}",
        ]
    return "\n".join(lines)


def build_gap_roadmap_messages(
    ranked_careers: list[RankedCareerInput],
    gaps_by_slug: dict[str, list[str]],
) -> list[dict]:
    """
    Build messages for the batched gap-tagging + roadmap call.

    Inputs:
      ranked_careers — the 5 LLM-ranked career objects
      gaps_by_slug   — pre-computed missing skills per slug (deterministic)

    Expected output: JSON matching GapRoadmapOutput schema.
    """
    user_content = "\n\n".join(
        [
            _format_gap_roadmap_input(ranked_careers, gaps_by_slug),
            "## Task\nFor each career above, tag the missing skills with difficulty "
            "and write the 3-phase learning roadmap. Return the JSON object.",
        ]
    )
    return [
        {"role": "system", "content": GAP_ROADMAP_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def build_gap_roadmap_messages_strict(
    ranked_careers: list[RankedCareerInput],
    gaps_by_slug: dict[str, list[str]],
    previous_response: str,
) -> list[dict]:
    """Retry prompt for gap+roadmap when the first attempt fails validation."""
    user_content = "\n\n".join(
        [
            _format_gap_roadmap_input(ranked_careers, gaps_by_slug),
            f"## Your Previous (Invalid) Response\n```\n{previous_response[:1500]}\n```",
            "## Task\nReturn a corrected JSON that matches the schema exactly.",
        ]
    )
    return [
        {"role": "system", "content": GAP_ROADMAP_SYSTEM_PROMPT_STRICT},
        {"role": "user", "content": user_content},
    ]


# ---------------------------------------------------------------------------
# Proposal — Stage 2.5: low-fit career suggestion
# Used in: services/proposer.py
# Temperature: 0.5 (needs creativity)   Max tokens: 1024
# ---------------------------------------------------------------------------

PROPOSAL_SYSTEM_PROMPT = """\
You are a career discovery assistant. The user's profile does not match standard \
occupations well. Suggest 1–2 emerging, niche, or hybrid careers that genuinely \
suit their skills, interests, and personality.

Return ONLY a valid JSON object — no markdown, no code fences, no text outside:

{
  "proposed_careers": [
    {
      "name": "<specific career title>",
      "description": "<exactly 2 sentences, at least 50 characters total>",
      "category": "<broad occupational category>",
      "required_skills": ["<skill>", "..."],
      "optional_skills": ["<skill>", "..."],
      "personality_fit": {
        "openness": <0-100>,
        "conscientiousness": <0-100>,
        "extraversion": <0-100>,
        "agreeableness": <0-100>,
        "neuroticism": <0-100>
      },
      "difficulty": "low|medium|high",
      "growth_potential": "low|medium|high",
      "rationale": "<2-3 sentences specific to this user's profile>"
    }
  ]
}

Rules:
- proposed_careers: 1 or 2 items — do not exceed 2
- name: a plausible real or emerging career title, not generic like "Tech Worker"
- required_skills: 5–8 specific, learnable skills
- optional_skills: 0–5 items (empty list is acceptable)
- description: minimum 50 characters total
- rationale: must reference this user's actual skills, interests, or personality traits
- Do NOT propose careers that closely duplicate the existing poor-match careers listed
- All personality_fit values must be integers 0–100
"""

PROPOSAL_SYSTEM_PROMPT_STRICT = """\
Your previous response did not match the required schema. Fix it now.

Required JSON:
{
  "proposed_careers": [
    {
      "name": "<string, min 3 chars>",
      "description": "<string, min 50 chars>",
      "category": "<string>",
      "required_skills": ["<5 to 8 strings>"],
      "optional_skills": ["<0 to 5 strings>"],
      "personality_fit": {"openness":<int>,"conscientiousness":<int>,"extraversion":<int>,"agreeableness":<int>,"neuroticism":<int>},
      "difficulty": "low|medium|high",
      "growth_potential": "low|medium|high",
      "rationale": "<string, min 20 chars>"
    }
  ]
}

CRITICAL:
- 1 or 2 items in proposed_careers — not 0, not 3+
- All personality_fit values must be integers (not strings, not floats)
- required_skills must have 5–8 items
- Return ONLY the JSON object, nothing else
"""


def build_proposal_messages(
    profile: ProfileData,
    poor_match_names: list[str],
) -> list[dict]:
    """
    Build messages for the LLM career proposal call.

    Inputs:
      profile          — the user's profile data dict
      poor_match_names — names of the top-scoring verified careers (context for what NOT to duplicate)

    Expected output: JSON matching ProposalOutput schema (1–2 proposed careers).
    """
    existing_list = "\n".join(f"- {n}" for n in poor_match_names[:5])
    user_content = "\n\n".join(
        [
            _format_profile(profile),
            f"## Existing Careers (poor matches — do not duplicate these)\n{existing_list}",
            "## Task\nPropose 1–2 emerging or niche careers that would genuinely suit "
            "this user better. Return the JSON object described in the system prompt.",
        ]
    )
    return [
        {"role": "system", "content": PROPOSAL_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def build_proposal_messages_strict(
    profile: ProfileData,
    poor_match_names: list[str],
    previous_response: str,
) -> list[dict]:
    """Retry prompt for proposal when the first attempt fails validation."""
    existing_list = "\n".join(f"- {n}" for n in poor_match_names[:5])
    user_content = "\n\n".join(
        [
            _format_profile(profile),
            f"## Existing Careers (poor matches)\n{existing_list}",
            f"## Your Previous (Invalid) Response\n```\n{previous_response[:1000]}\n```",
            "## Task\nReturn a corrected JSON that matches the schema exactly.",
        ]
    )
    return [
        {"role": "system", "content": PROPOSAL_SYSTEM_PROMPT_STRICT},
        {"role": "user", "content": user_content},
    ]


# ---------------------------------------------------------------------------
# Analyze — single career gap tagging for /api/analyze
# Used in: services/gap_analyzer.py
# Temperature: 0.2   Max tokens: 512   Model: groq_model_extraction
# ---------------------------------------------------------------------------

ANALYZE_SYSTEM_PROMPT = """\
You are a career skills assessor. Tag each provided skill with a learning \
difficulty level based on typical learning curves for someone entering \
this career field.

Return ONLY a valid JSON object:
{
  "slug": "<career slug>",
  "skill_gaps": [
    {"skill": "<skill name>", "difficulty": "easy|medium|hard"}
  ]
}

Difficulty criteria:
  easy   — learnable in days/weeks with adjacent experience
  medium — weeks to months of focused study
  hard   — months to a year or requires deep prior knowledge

Include ALL provided skills in the same order. No extra text outside the JSON.
"""

ANALYZE_SYSTEM_PROMPT_STRICT = """\
Fix your previous response to match this exact schema:
{
  "slug": "<string>",
  "skill_gaps": [{"skill": "<string>", "difficulty": "easy|medium|hard"}]
}
- Include ALL skills from the input.
- difficulty must be exactly "easy", "medium", or "hard" (lowercase).
- Return ONLY the JSON.
"""


def build_analyze_messages(
    career_slug: str,
    career_name: str,
    missing_skills: list[str],
) -> list[dict]:
    """
    Build messages for single-career gap-tagging (/api/analyze).

    Inputs:
      career_slug    — slug of the career being analysed
      career_name    — human-readable name (context for the model)
      missing_skills — skills the user lacks for this career

    Expected output: JSON matching AnalyzeOutput schema.
    """
    skills_list = "\n".join(f"- {s}" for s in missing_skills)
    user_content = (
        f"Career: {career_name} (slug: {career_slug})\n\n"
        f"Skills to tag:\n{skills_list}\n\n"
        "Return the JSON object described in the system prompt."
    )
    return [
        {"role": "system", "content": ANALYZE_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def build_analyze_messages_strict(
    career_slug: str,
    career_name: str,
    missing_skills: list[str],
    previous_response: str,
) -> list[dict]:
    """Retry prompt for analyze when the first attempt fails validation."""
    skills_list = "\n".join(f"- {s}" for s in missing_skills)
    user_content = (
        f"Career: {career_name} (slug: {career_slug})\n\n"
        f"Skills to tag:\n{skills_list}\n\n"
        f"Previous (invalid) response:\n```\n{previous_response[:500]}\n```\n\n"
        "Return ONLY the corrected JSON."
    )
    return [
        {"role": "system", "content": ANALYZE_SYSTEM_PROMPT_STRICT},
        {"role": "user", "content": user_content},
    ]
