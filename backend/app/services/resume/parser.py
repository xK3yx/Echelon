"""
Text extraction from PDF, DOCX, and plain-text resume files.

Extraction order for PDFs:
  1. pypdf (fast, works for text-based PDFs)
  2. pdfplumber (slower but more layout-aware; used as fallback)
  3. Raise ValueError("scanned_pdf") if both yield < 100 characters

Raises:
  ValueError("scanned_pdf")     — PDF appears to be scanned / image-only
  Exception                      — any other IO / parsing failure (caller wraps)
"""
from __future__ import annotations

import io

_MIN_TEXT_LENGTH = 100


def extract_text(file_bytes: bytes, mime_type: str) -> str:
    """Dispatch to the correct extractor based on MIME type."""
    if mime_type == "application/pdf":
        return _extract_pdf(file_bytes)
    if mime_type == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        return _extract_docx(file_bytes)
    # text/plain (and any other allowed type)
    return _extract_txt(file_bytes)


# ---------------------------------------------------------------------------
# Internal extractors
# ---------------------------------------------------------------------------


def _extract_pdf(file_bytes: bytes) -> str:
    import pypdf

    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()

    if len(text) < _MIN_TEXT_LENGTH:
        # Fallback: pdfplumber handles more complex layouts
        import pdfplumber

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages).strip()

    if len(text) < _MIN_TEXT_LENGTH:
        raise ValueError("scanned_pdf")

    return text


def _extract_docx(file_bytes: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    parts: list[str] = []

    for para in doc.paragraphs:
        stripped = para.text.strip()
        if stripped:
            parts.append(stripped)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                stripped = cell.text.strip()
                if stripped:
                    parts.append(stripped)

    return "\n".join(parts)


def _extract_txt(file_bytes: bytes) -> str:
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1")
