"""
Tests for POST /api/resume/parse — multipart resume upload and structured extraction.

Covers:
  Unit (no IO, no mocks):
    · heuristic scorer on valid resume text  → score >= 3
    · heuristic scorer on research-paper text → score < 3

  Integration (HTTP client, LLM mocked via monkeypatch):
    · file_too_large      — file > MAX_UPLOAD_SIZE_MB → 400
    · unsupported_type    — JPEG magic bytes → 400
    · no_resume_keywords  — non-resume text rejected by heuristic → 400
    · valid parse         — valid resume + good LLM response → 200
    · llm_says_not_resume — LLM returns is_resume=False → 400
    · low_confidence      — LLM returns confidence=0.3, combined < threshold → 400
    · extraction_failed   — LLM returns invalid JSON on both attempts → 400
"""
from __future__ import annotations

import json
import pathlib
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.services.resume.validator import score_heuristic

# ---------------------------------------------------------------------------
# Fixture file bytes (loaded once at module import — small txt files)
# ---------------------------------------------------------------------------

_FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "resumes"
_VALID_RESUME_BYTES: bytes = (_FIXTURES / "valid_resume.txt").read_bytes()
_NON_RESUME_BYTES: bytes = (_FIXTURES / "non_resume.txt").read_bytes()

# ---------------------------------------------------------------------------
# LLM mock payloads
# ---------------------------------------------------------------------------

_GOOD_LLM_RESPONSE = {
    "is_resume": True,
    "name": "Jane Smith",
    "email": "jane.smith@email.example",
    "skills": ["Python", "JavaScript", "TypeScript", "SQL", "Go"],
    "education_level": "bachelors",
    "interests": ["Backend Development", "Distributed Systems"],
    "years_experience": 5,
    "summary": "Results-driven software engineer with 5 years of professional experience.",
    "confidence": 0.9,
}

_NOT_RESUME_LLM_RESPONSE = {
    "is_resume": False,
    "reason": "This appears to be a research paper, not a resume.",
}

# confidence=0.3: combined with heuristic 5/5 → 1.0 * 0.3 = 0.30 < threshold (0.4)
_LOW_CONFIDENCE_LLM_RESPONSE = {
    "is_resume": True,
    "name": "Jane Smith",
    "email": "jane.smith@email.example",
    "skills": ["Python"],
    "education_level": "bachelors",
    "interests": ["Software"],
    "years_experience": 5,
    "summary": "Software engineer.",
    "confidence": 0.3,
}


def _mock_llm(payload: dict) -> AsyncMock:
    """Simulate a successful groq.chat_completion returning *payload* as JSON."""
    return AsyncMock(
        return_value={
            "choices": [{"message": {"content": json.dumps(payload)}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 200},
        }
    )


def _mock_llm_invalid_json() -> AsyncMock:
    """Simulate groq returning malformed JSON — causes both extraction attempts to fail."""
    return AsyncMock(
        return_value={
            "choices": [{"message": {"content": "this is not valid json {"}}],
            "usage": {},
        }
    )


# ---------------------------------------------------------------------------
# Unit tests — heuristic scorer (pure function, no IO, no mocks)
# ---------------------------------------------------------------------------


def test_heuristic_scores_valid_resume():
    """valid_resume.txt hits all 5 criteria → score 5/5 (at minimum >= 3)."""
    text = _VALID_RESUME_BYTES.decode("utf-8")
    result = score_heuristic(text)
    assert result.score >= 3, (
        f"Expected heuristic score >= 3, got {result.score}. "
        f"Criteria met: {result.reasons}, word_count={result.word_count}"
    )


def test_heuristic_scores_non_resume():
    """non_resume.txt (research paper) has no career/education/skill keywords → score < 3."""
    text = _NON_RESUME_BYTES.decode("utf-8")
    result = score_heuristic(text)
    assert result.score < 3, (
        f"Expected heuristic score < 3, got {result.score}. "
        f"Criteria met: {result.reasons}, word_count={result.word_count}"
    )


# ---------------------------------------------------------------------------
# Integration tests — POST /api/resume/parse
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parse_file_too_large(client: AsyncClient):
    """Files exceeding MAX_UPLOAD_SIZE_MB (5 MB) must be rejected with file_too_large."""
    large_bytes = b"x" * (6 * 1024 * 1024)  # 6 MB
    response = await client.post(
        "/api/resume/parse",
        files={"file": ("big.txt", large_bytes, "text/plain")},
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "INVALID_RESUME"
    assert error["details"]["reason"] == "file_too_large"


@pytest.mark.asyncio
async def test_parse_unsupported_mime(client: AsyncClient):
    """Bytes with JPEG magic header must be rejected with unsupported_type."""
    # FF D8 FF E0 is the canonical JPEG/JFIF magic — libmagic reliably detects image/jpeg
    jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 512
    response = await client.post(
        "/api/resume/parse",
        files={"file": ("photo.jpg", jpeg_bytes, "image/jpeg")},
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "INVALID_RESUME"
    assert error["details"]["reason"] == "unsupported_type"


@pytest.mark.asyncio
async def test_parse_non_resume_text(client: AsyncClient):
    """
    A research-paper .txt file (heuristic score < 3) must be rejected before the LLM
    is even called — reason: no_resume_keywords.
    """
    response = await client.post(
        "/api/resume/parse",
        files={"file": ("paper.txt", _NON_RESUME_BYTES, "text/plain")},
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "INVALID_RESUME"
    assert error["details"]["reason"] == "no_resume_keywords"


@pytest.mark.asyncio
async def test_parse_valid_resume(client: AsyncClient, monkeypatch):
    """Valid resume text + successful LLM extraction → 200 with all expected fields."""
    import app.services.resume.extractor as extractor_mod

    monkeypatch.setattr(
        extractor_mod.groq, "chat_completion", _mock_llm(_GOOD_LLM_RESPONSE)
    )

    response = await client.post(
        "/api/resume/parse",
        files={"file": ("resume.txt", _VALID_RESUME_BYTES, "text/plain")},
    )

    assert response.status_code == 200
    body = response.json()

    assert "extracted" in body
    assert "confidence" in body
    assert "warnings" in body

    ext = body["extracted"]
    assert ext["name"] == "Jane Smith"
    assert ext["email"] == "jane.smith@email.example"
    assert ext["education_level"] == "bachelors"
    assert isinstance(ext["skills"], list)
    assert len(ext["skills"]) > 0
    assert ext["years_experience"] == 5

    # Combined confidence must be > 0 (heuristic_score/5 * llm_confidence)
    assert body["confidence"] > 0.0


@pytest.mark.asyncio
async def test_parse_llm_says_not_resume(client: AsyncClient, monkeypatch):
    """
    When the LLM returns is_resume=False, the endpoint must reject with
    no_resume_keywords — even though the heuristic passed.
    """
    import app.services.resume.extractor as extractor_mod

    monkeypatch.setattr(
        extractor_mod.groq,
        "chat_completion",
        _mock_llm(_NOT_RESUME_LLM_RESPONSE),
    )

    response = await client.post(
        "/api/resume/parse",
        files={"file": ("resume.txt", _VALID_RESUME_BYTES, "text/plain")},
    )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "INVALID_RESUME"
    assert error["details"]["reason"] == "no_resume_keywords"


@pytest.mark.asyncio
async def test_parse_low_confidence(client: AsyncClient, monkeypatch):
    """
    LLM confidence=0.3 with heuristic score 5/5 → combined=0.30 < threshold (0.4)
    → 400 with reason low_confidence.
    """
    import app.services.resume.extractor as extractor_mod

    monkeypatch.setattr(
        extractor_mod.groq,
        "chat_completion",
        _mock_llm(_LOW_CONFIDENCE_LLM_RESPONSE),
    )

    response = await client.post(
        "/api/resume/parse",
        files={"file": ("resume.txt", _VALID_RESUME_BYTES, "text/plain")},
    )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "INVALID_RESUME"
    assert error["details"]["reason"] == "low_confidence"


@pytest.mark.asyncio
async def test_parse_extraction_failed(client: AsyncClient, monkeypatch):
    """
    LLM returning invalid JSON on both extraction attempts must yield
    400 with reason extraction_failed.
    """
    import app.services.resume.extractor as extractor_mod

    monkeypatch.setattr(
        extractor_mod.groq, "chat_completion", _mock_llm_invalid_json()
    )

    response = await client.post(
        "/api/resume/parse",
        files={"file": ("resume.txt", _VALID_RESUME_BYTES, "text/plain")},
    )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "INVALID_RESUME"
    assert error["details"]["reason"] == "extraction_failed"
