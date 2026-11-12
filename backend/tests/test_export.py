"""PDF export renders for real through WeasyPrint (no mocking)."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation import Recommendation
from app.routers import export

from .test_api import VALID_PROFILE

pytestmark = pytest.mark.skipif(
    not export._WEASYPRINT_AVAILABLE, reason="WeasyPrint system libraries not installed"
)

_CAREER = {
    "name": "Data Scientist",
    "slug": "data-scientist",
    "source": "manual",
    "category": "Data & Analytics",
    "confidence": 82.4,
    "fit_reasoning": "Strong Python and SQL background.",
    "strengths": ["Python", "SQL"],
    "risks": ["Limited statistics"],
    "rule_scores": {"skill": 0.3, "personality": 0.2, "interest": 0.1},
    "skill_gaps": [{"skill": "Statistics", "difficulty": "medium"}],
    "roadmap": [
        {"phase": "Beginner", "duration_weeks": 6, "skills": ["Statistics"], "projects": ["A", "B"]}
    ],
}


async def test_export_pdf_renders(client: AsyncClient, db: AsyncSession):
    profile = (await client.post("/api/profiles", json=VALID_PROFILE)).json()
    rec = Recommendation(
        profile_id=profile["id"],
        result={"ranked_careers": [_CAREER], "proposed_careers": []},
        model_used="test-model",
    )
    db.add(rec)
    await db.commit()

    response = await client.get(f"/api/recommendations/{rec.id}/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
