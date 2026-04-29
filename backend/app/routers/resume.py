"""
POST /api/resume/parse — multipart resume upload with structured extraction.

Validation chain (fail-fast):
  1. File size ≤ MAX_UPLOAD_SIZE_MB
  2. MIME type via libmagic (not the Content-Type header)
  3. Text extraction (pypdf → pdfplumber for PDFs; python-docx for DOCX)
  4. Heuristic resume detection (score ≥ 3/5)
  5. LLM extraction (with is_resume check; retries once on failure)
  6. Combined confidence threshold
"""
import logging
from typing import Annotated

import magic
from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.config import settings
from app.limiter import limiter
from app.llm.client import GroqError
from app.services.resume.extractor import extract_via_llm
from app.services.resume.parser import extract_text
from app.services.resume.schemas import ExtractedProfile, ResumeParseResponse
from app.services.resume.validator import score_heuristic

logger = logging.getLogger(__name__)

router = APIRouter(tags=["resume"])

_ALLOWED_MIMES: frozenset[str] = frozenset(
    {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    }
)
_LEGACY_DOC_MIME = "application/msword"

_HEURISTIC_PASS_THRESHOLD = 3


def _resume_error(
    code: str,
    message: str,
    reason: str,
    status: int = 400,
) -> HTTPException:
    """Build a structured 400 error consistent with the Echelon error envelope."""
    return HTTPException(
        status_code=status,
        detail={"code": code, "message": message, "details": {"reason": reason}},
    )


@router.post("/resume/parse", response_model=ResumeParseResponse)
@limiter.limit("10/hour")
async def parse_resume(
    request: Request,
    file: Annotated[
        UploadFile,
        File(description="Resume file — PDF, DOCX, or TXT. Max 5 MB."),
    ],
) -> ResumeParseResponse:
    """
    Parse a resume and return structured profile data for form prefill.

    Error codes returned in details.reason:
      file_too_large     — file exceeds MAX_UPLOAD_SIZE_MB
      unsupported_type   — MIME type not in {pdf, docx, txt}; also .doc files
      scanned_pdf        — PDF contains no extractable text (likely scanned)
      extraction_failed  — text/LLM extraction failure
      no_resume_keywords — heuristic or LLM determined it is not a resume
      low_confidence     — combined confidence below threshold
    """
    # ── 1. File size ──────────────────────────────────────────────────────────
    file_bytes = await file.read()
    max_bytes = int(settings.max_upload_size_mb * 1024 * 1024)
    if len(file_bytes) > max_bytes:
        raise _resume_error(
            "INVALID_RESUME",
            f"File is too large. Maximum allowed size is {settings.max_upload_size_mb} MB.",
            reason="file_too_large",
        )

    # ── 2. MIME type (from magic bytes, not filename) ─────────────────────────
    detected_mime: str = magic.from_buffer(file_bytes, mime=True)

    if detected_mime == _LEGACY_DOC_MIME:
        raise _resume_error(
            "INVALID_RESUME",
            "Legacy .doc files are not supported. "
            "Please save your resume as .docx or PDF and try again.",
            reason="unsupported_type",
        )

    if detected_mime not in _ALLOWED_MIMES:
        raise _resume_error(
            "INVALID_RESUME",
            f"Unsupported file type ({detected_mime}). "
            "Please upload a PDF, DOCX, or plain-text (.txt) file.",
            reason="unsupported_type",
        )

    # ── 3. Text extraction ────────────────────────────────────────────────────
    try:
        text = extract_text(file_bytes, detected_mime)
    except ValueError as exc:
        if str(exc) == "scanned_pdf":
            raise _resume_error(
                "INVALID_RESUME",
                "This appears to be a scanned PDF with no extractable text. "
                "Please upload a text-based PDF or paste your resume as a .txt file.",
                reason="scanned_pdf",
            ) from exc
        raise _resume_error(
            "INVALID_RESUME",
            "Failed to extract text from the file.",
            reason="extraction_failed",
        ) from exc
    except Exception:
        logger.exception("Unexpected error during resume text extraction")
        raise _resume_error(
            "INVALID_RESUME",
            "The file could not be read — it may be corrupt or password-protected.",
            reason="extraction_failed",
        )

    # ── 4. Heuristic resume detection ─────────────────────────────────────────
    heuristic = score_heuristic(text)
    if heuristic.score < _HEURISTIC_PASS_THRESHOLD:
        raise _resume_error(
            "INVALID_RESUME",
            f"This file does not appear to be a resume "
            f"(heuristic score: {heuristic.score}/5). "
            "Please upload your resume or fill in the form manually.",
            reason="no_resume_keywords",
        )

    # ── 5. LLM extraction ─────────────────────────────────────────────────────
    warnings: list[str] = []
    try:
        llm_output, llm_warnings = await extract_via_llm(
            text, model=settings.groq_model_extraction
        )
        warnings.extend(llm_warnings)
    except GroqError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM error during resume extraction: {exc}",
        ) from exc
    except ValueError:
        raise _resume_error(
            "INVALID_RESUME",
            "The resume structure could not be parsed after two attempts. "
            "Please fill in the form manually.",
            reason="extraction_failed",
        )

    if not llm_output.is_resume:
        raise _resume_error(
            "INVALID_RESUME",
            f"The uploaded file does not appear to be a resume"
            f"{': ' + llm_output.reason if llm_output.reason else ''}. "
            "Please fill in the form manually.",
            reason="no_resume_keywords",
        )

    # ── 6. Combined confidence threshold ──────────────────────────────────────
    combined = round((heuristic.score / 5.0) * llm_output.confidence, 3)
    if combined < settings.resume_confidence_threshold:
        raise _resume_error(
            "INVALID_RESUME",
            "We couldn't reliably parse this resume "
            f"(confidence: {combined:.0%}). "
            "Please fill in the form manually.",
            reason="low_confidence",
        )

    # Warn about fields that could not be determined
    if llm_output.education_level is None:
        warnings.append(
            "Education level could not be determined — please set it manually."
        )
    if not llm_output.skills:
        warnings.append(
            "No skills were detected — please add them manually."
        )

    return ResumeParseResponse(
        extracted=ExtractedProfile(
            name=llm_output.name,
            email=llm_output.email,
            skills=llm_output.skills,
            education_level=llm_output.education_level,
            interests=llm_output.interests,
            years_experience=llm_output.years_experience,
            summary=llm_output.summary,
        ),
        confidence=combined,
        warnings=warnings,
    )
