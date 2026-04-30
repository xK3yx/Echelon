"""
Attachment processing for Vantage chat messages.

Handles three kinds of uploads:
  - PDF/DOCX/TXT: extract text via the resume parser, return excerpt
  - Image: keep raw bytes for the vision-model call, store no excerpt

The excerpt is stored on the chat_messages row so future turns of the
conversation can reference what was attached without re-processing the
file. Binary bytes are NEVER persisted.
"""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass

import magic

from app.services.resume.parser import extract_text

logger = logging.getLogger(__name__)

_ALLOWED_DOC_MIMES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
}
_ALLOWED_IMAGE_MIMES = {
    "image/png": "png",
    "image/jpeg": "jpeg",
    "image/webp": "webp",
    "image/gif": "gif",
}

# Cap excerpt to keep token usage manageable; the full document is sent
# as context only on the message it was attached to.
_EXCERPT_MAX_CHARS = 4000

# Cap attachment file size so users can't blow the LLM context window
_MAX_ATTACHMENT_SIZE_MB = 10


@dataclass
class ProcessedAttachment:
    kind: str  # "pdf" | "docx" | "txt" | "image"
    name: str
    mime: str
    excerpt: str | None  # extracted text for documents
    image_data_url: str | None  # data:<mime>;base64,... for images


class AttachmentError(ValueError):
    """Raised on rejected attachments. Caller maps to HTTP 400."""


def process(file_bytes: bytes, filename: str) -> ProcessedAttachment:
    """
    Detect MIME via libmagic, validate, and extract the relevant payload.

    Raises AttachmentError on size limit, unsupported type, or extraction
    failure. The caller (chat router) translates that to a 400 response.
    """
    if len(file_bytes) > _MAX_ATTACHMENT_SIZE_MB * 1024 * 1024:
        raise AttachmentError(
            f"Attachment exceeds {_MAX_ATTACHMENT_SIZE_MB} MB limit."
        )

    detected_mime: str = magic.from_buffer(file_bytes, mime=True)

    if detected_mime in _ALLOWED_DOC_MIMES:
        kind = _ALLOWED_DOC_MIMES[detected_mime]
        try:
            text = extract_text(file_bytes, detected_mime)
        except ValueError as exc:
            if str(exc) == "scanned_pdf":
                raise AttachmentError(
                    "This PDF appears to be scanned with no readable text."
                ) from exc
            raise AttachmentError("Failed to extract text from the file.") from exc
        excerpt = text[:_EXCERPT_MAX_CHARS]
        if len(text) > _EXCERPT_MAX_CHARS:
            excerpt += "\n[... truncated ...]"
        return ProcessedAttachment(
            kind=kind,
            name=filename,
            mime=detected_mime,
            excerpt=excerpt,
            image_data_url=None,
        )

    if detected_mime in _ALLOWED_IMAGE_MIMES:
        b64 = base64.b64encode(file_bytes).decode("ascii")
        return ProcessedAttachment(
            kind="image",
            name=filename,
            mime=detected_mime,
            excerpt=None,
            image_data_url=f"data:{detected_mime};base64,{b64}",
        )

    raise AttachmentError(
        f"Unsupported attachment type ({detected_mime}). "
        "Use PDF, DOCX, TXT, PNG, JPEG, WEBP, or GIF."
    )
