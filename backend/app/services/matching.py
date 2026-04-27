"""
Rule-based career scoring — fully deterministic, no LLM involved.

Scoring components (all in [0, 1] except optional which is [0, 0.3]):
  skill       = required-skill overlap ratio
  optional    = optional-skill overlap ratio × 0.3
  personality = 1 − mean(|user_trait − ideal_trait|) / 100
  interest    = fraction of user interests found as substrings in career corpus

Weighted total (weights sum to 1.0):
  0.45 × skill  +  0.15 × optional  +  0.25 × personality  +  0.15 × interest

Education soft penalty (applied after the weighted sum):
  If the user's education_level is "high_school" and the career's difficulty
  is "high" (corresponding to O*NET Job Zones 4–5), the total score is
  multiplied by 0.7.  The career is NOT filtered out — it remains visible
  as a stretch goal.  No penalty applies for any other education/difficulty
  combination.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NotRequired, Required, TypedDict

# ---------------------------------------------------------------------------
# Input types (plain dicts — no ORM dependency so this module is easily tested)
# ---------------------------------------------------------------------------

PERSONALITY_KEYS = ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism")

WEIGHTS = {
    "skill": 0.45,
    "optional": 0.15,
    "personality": 0.25,
    "interest": 0.15,
}

# Multiply total score by this factor when user has high_school education
# and the career requires high preparation (difficulty = "high").
EDUCATION_PENALTY_FACTOR = 0.7


class ProfileData(TypedDict):
    skills: Required[list[str]]
    interests: Required[list[str]]
    personality: Required[dict[str, int]]
    education_level: NotRequired[str]  # omitting = no education penalty applied


class CareerData(TypedDict):
    id: str
    slug: str
    name: str
    category: str
    description: str
    required_skills: list[str]
    optional_skills: list[str]
    personality_fit: dict[str, int]
    difficulty: NotRequired[str]  # omitting = no education penalty applied


# ---------------------------------------------------------------------------
# Output type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScoredCareer:
    career_id: str
    slug: str
    name: str
    category: str
    total_score: float
    skill_score: float
    optional_score: float
    personality_score: float
    interest_score: float


# ---------------------------------------------------------------------------
# Individual scoring functions (public so unit tests can call them directly)
# ---------------------------------------------------------------------------


def compute_skill_score(user_skills: set[str], required_skills: list[str]) -> float:
    """Fraction of required skills the user possesses (case-insensitive)."""
    if not required_skills:
        return 1.0
    normalized = {s.lower() for s in user_skills}
    required = {s.lower() for s in required_skills}
    return len(normalized & required) / len(required)


def compute_optional_score(user_skills: set[str], optional_skills: list[str]) -> float:
    """Optional-skill overlap ratio scaled by 0.3, yielding a value in [0, 0.3]."""
    if not optional_skills:
        return 0.0
    optional = {s.lower() for s in optional_skills}
    overlap_ratio = len(user_skills & optional) / max(1, len(optional))
    return overlap_ratio * 0.3


def compute_personality_score(
    user_personality: dict[str, int],
    career_personality_fit: dict[str, int],
) -> float:
    """1 minus the normalised mean absolute deviation across Big Five traits."""
    diffs = [abs(user_personality[k] - career_personality_fit[k]) for k in PERSONALITY_KEYS]
    return 1.0 - (sum(diffs) / len(diffs)) / 100.0


def compute_interest_score(interests: list[str], career: CareerData) -> float:
    """Fraction of user interests that appear (as substrings) in the career corpus."""
    if not interests:
        return 0.0
    corpus = " ".join(
        [career["name"].lower(), career["category"].lower(), career["description"].lower()]
    )
    matched = sum(1 for interest in interests if interest.lower() in corpus)
    return matched / len(interests)


def apply_education_penalty(total_score: float, education_level: str, difficulty: str) -> float:
    """
    Apply a soft downrank for under-qualified profiles.

    Rule: high_school education + high difficulty career → multiply by 0.7.
    All other combinations are unchanged.
    The career is never filtered out — it remains a visible stretch goal.
    """
    if education_level == "high_school" and difficulty == "high":
        return total_score * EDUCATION_PENALTY_FACTOR
    return total_score


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def rank_careers(profile: ProfileData, careers: list[CareerData]) -> list[ScoredCareer]:
    """
    Score every career against the profile and return the top 10, best first.

    This is the sole public entry point for the rule-based stage.  The LLM
    re-ranker (services/ranker.py) takes the output of this function and
    produces the final top 5.
    """
    user_skills = {s.lower() for s in profile["skills"]}
    education_level = profile.get("education_level", "")

    scored: list[ScoredCareer] = []
    for career in careers:
        skill = compute_skill_score(user_skills, career["required_skills"])
        optional = compute_optional_score(user_skills, career["optional_skills"])
        personality = compute_personality_score(profile["personality"], career["personality_fit"])
        interest = compute_interest_score(profile["interests"], career)

        total = (
            WEIGHTS["skill"] * skill
            + WEIGHTS["optional"] * optional
            + WEIGHTS["personality"] * personality
            + WEIGHTS["interest"] * interest
        )

        total = apply_education_penalty(total, education_level, career.get("difficulty", ""))

        scored.append(
            ScoredCareer(
                career_id=career["id"],
                slug=career["slug"],
                name=career["name"],
                category=career["category"],
                total_score=round(total, 6),
                skill_score=round(skill, 6),
                optional_score=round(optional, 6),
                personality_score=round(personality, 6),
                interest_score=round(interest, 6),
            )
        )

    return sorted(scored, key=lambda s: s.total_score, reverse=True)[:10]
