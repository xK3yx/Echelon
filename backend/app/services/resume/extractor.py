"""
LLM-based structured extraction from resume text.

Two-attempt strategy:
  Attempt 1: temperature=0.3, standard prompt
  Attempt 2: temperature=0.1, stricter prompt (no markdown, minimal output)

Raises ValueError("extraction_failed") if both attempts fail validation.
"""
from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from app.llm import client as groq
from app.services.resume.schemas import LLMResumeOutput

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_SYSTEM = """\
You are a resume parser. Extract structured information from the resume text provided.

If the text is NOT a resume (e.g. a research paper, cover letter, news article, or other
document), respond with exactly:
{"is_resume": false, "reason": "<brief explanation>"}

If it IS a resume, respond with this JSON object:
{
  "is_resume": true,
  "name": "<full name or null>",
  "email": "<email address or null>",
  "skills": ["<technical or professional skill>", ...],
  "education_level": "<high_school|diploma|bachelors|masters|phd or null>",
  "interests": ["<professional domain or topic>", ...],
  "years_experience": <approximate total years of work experience as integer or null>,
  "summary": "<1-2 sentence professional summary or null>",
  "confidence": <0.0–1.0 reflecting how complete and clear the extraction was>
}

Respond ONLY with valid JSON. No markdown fences, no explanation outside the JSON.\
"""

_SYSTEM_STRICT = _SYSTEM + (
    "\n\nCRITICAL: Output ONLY the raw JSON object. "
    "Do not wrap in ```json``` or add any surrounding text."
)

# Only the first 6 000 characters are sent to stay within token budget
_MAX_TEXT_CHARS = 6_000


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


async def extract_via_llm(
    text: str,
    model: str,
) -> tuple[LLMResumeOutput, list[str]]:
    """
    Extract structured resume fields via Groq.

    Returns:
        (LLMResumeOutput, warnings)

    Raises:
        ValueError("extraction_failed") if both attempts fail.
        GroqError — if the API key is missing or the API returns non-200.
    """
    warnings: list[str] = []
    attempts = [
        (0.3, _SYSTEM),
        (0.1, _SYSTEM_STRICT),
    ]

    for attempt_idx, (temperature, system_prompt) in enumerate(attempts):
        try:
            resp = await groq.chat_completion(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Parse this resume:\n\n{text[:_MAX_TEXT_CHARS]}",
                    },
                ],
                temperature=temperature,
                max_tokens=512,
                response_format={"type": "json_object"},
            )
            raw_content = resp["choices"][0]["message"]["content"]
            parsed_data = json.loads(raw_content)
            return LLMResumeOutput(**parsed_data), warnings

        except (ValidationError, json.JSONDecodeError, KeyError) as exc:
            logger.warning(
                "resume_extract attempt=%d failed: %s", attempt_idx + 1, exc
            )
            if attempt_idx == 0:
                warnings.append(
                    "First extraction attempt failed; retried with a stricter prompt."
                )
            else:
                raise ValueError("extraction_failed") from exc

    # Should be unreachable, but satisfies type checkers
    raise ValueError("extraction_failed")
