"""
Heuristic resume detection — no LLM, no IO, fully unit-testable.

Scores a text on 5 criteria (0–5).  Callers should reject texts scoring < 3.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

EXPERIENCE_KEYWORDS: frozenset[str] = frozenset(
    {"experience", "employment", "work history", "professional", "career"}
)
EDUCATION_KEYWORDS: frozenset[str] = frozenset(
    {
        "education",
        "university",
        "college",
        "bachelor",
        "master",
        "degree",
        "diploma",
        "school",
    }
)
SKILL_KEYWORDS: frozenset[str] = frozenset(
    {"skills", "competencies", "technologies", "proficient", "languages"}
)

_DATE_RE = re.compile(r"\b(19|20)\d{2}\b")

MIN_WORD_COUNT = 200
MAX_WORD_COUNT = 10_000


@dataclass
class HeuristicResult:
    score: int  # 0–5
    reasons: list[str] = field(default_factory=list)
    word_count: int = 0


def score_heuristic(text: str) -> HeuristicResult:
    """
    Score text on five resume-detection criteria.

    Criteria (+1 each):
      1. ≥1 experience keyword
      2. ≥1 education keyword
      3. ≥1 skill keyword
      4. ≥2 four-digit year patterns (e.g. 2019)
      5. Word count in [200, 10_000]
    """
    lower = text.lower()
    score = 0
    reasons: list[str] = []

    if any(kw in lower for kw in EXPERIENCE_KEYWORDS):
        score += 1
        reasons.append("experience_keywords")

    if any(kw in lower for kw in EDUCATION_KEYWORDS):
        score += 1
        reasons.append("education_keywords")

    if any(kw in lower for kw in SKILL_KEYWORDS):
        score += 1
        reasons.append("skill_keywords")

    if len(_DATE_RE.findall(text)) >= 2:
        score += 1
        reasons.append("date_patterns")

    word_count = len(text.split())
    if MIN_WORD_COUNT <= word_count <= MAX_WORD_COUNT:
        score += 1
        reasons.append("word_count_in_range")

    return HeuristicResult(score=score, reasons=reasons, word_count=word_count)
