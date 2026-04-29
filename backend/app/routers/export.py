"""
GET /api/recommendations/{id}/pdf — render a career report as a PDF.

Uses WeasyPrint to render a Jinja2 HTML template.  The recommendation must
exist; no is_public check — the owner (who has the UUID) can download their
own report.

WeasyPrint requires libcairo + libpango on the host (installed in the
production Dockerfile).  If the import fails at startup the endpoint is
registered but returns 503 so the rest of the API keeps working.
"""
from __future__ import annotations

import asyncio
import logging
import pathlib
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.recommendation import Recommendation

logger = logging.getLogger(__name__)

router = APIRouter(tags=["export"])

_TEMPLATES_DIR = pathlib.Path(__file__).parent.parent.parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)

_SOURCE_LABELS = {
    "onet": "O*NET",
    "manual": "Curated",
    "llm_proposed": "AI Suggested",
}

try:
    import weasyprint as _wp
    _WEASYPRINT_AVAILABLE = True
except Exception as _exc:  # pragma: no cover
    logger.warning("weasyprint not available — PDF export will return 503: %s", _exc)
    _wp = None  # type: ignore[assignment]
    _WEASYPRINT_AVAILABLE = False


@router.get("/recommendations/{recommendation_id}/pdf")
async def export_pdf(
    recommendation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    if not _WEASYPRINT_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="PDF export is not available in this environment.",
        )

    result = await db.execute(
        select(Recommendation).where(Recommendation.id == recommendation_id)
    )
    rec = result.scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    ranked_careers = rec.result.get("ranked_careers", [])
    proposed_careers = rec.result.get("proposed_careers", [])

    template = _jinja_env.get_template("report.html")
    html = template.render(
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        model_used=rec.model_used,
        ranked_careers=ranked_careers,
        proposed_careers=proposed_careers,
        source_labels=_SOURCE_LABELS,
    )

    # WeasyPrint's write_pdf() is synchronous and CPU-bound — offload it so
    # we don't block the event loop while rendering large reports.
    pdf_bytes = await asyncio.to_thread(_wp.HTML(string=html).write_pdf)

    short_id = str(recommendation_id)[:8]
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="echelon-report-{short_id}.pdf"'
        },
    )
