"""
Tests for admin career management endpoints.

Covers:
  - 401 when no token provided
  - 401 when wrong token provided
  - 503 when ADMIN_TOKEN env var is empty (feature disabled)
  - Full CRUD cycle (create → read → update → soft-delete)
  - Proposed career listing + verification flow
"""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import app.config as cfg
from app.models.career import Career

TEST_TOKEN = "test-admin-secret"
AUTH = {"Authorization": f"Bearer {TEST_TOKEN}"}
BAD_AUTH = {"Authorization": "Bearer wrong-token"}


@pytest.fixture(autouse=True)
def set_admin_token(monkeypatch):
    """Give every test in this module a valid ADMIN_TOKEN by default."""
    monkeypatch.setattr(cfg.settings, "admin_token", TEST_TOKEN)


def _career_payload(tag: str) -> dict:
    """Return a unique career payload for each test, keyed by tag."""
    return {
        "name": f"Quantum Computing Researcher {tag}",
        "slug": f"quantum-computing-researcher-{tag}",
        "description": "Research and develop quantum algorithms and hardware for next-generation computing.",
        "required_skills": ["Quantum Mechanics", "Linear Algebra", "Python", "Qiskit"],
        "optional_skills": ["C++", "Machine Learning"],
        "personality_fit": {
            "openness": 85,
            "conscientiousness": 80,
            "extraversion": 35,
            "agreeableness": 60,
            "neuroticism": 30,
        },
        "difficulty": "high",
        "growth_potential": "high",
        "category": "Computer & Mathematical",
        "source": "manual",
    }


# ---------------------------------------------------------------------------
# Auth guard tests
# ---------------------------------------------------------------------------


async def test_admin_no_token_returns_401(client: AsyncClient):
    response = await client.get("/api/admin/careers/proposed")
    assert response.status_code == 401


async def test_admin_wrong_token_returns_401(client: AsyncClient):
    response = await client.get("/api/admin/careers/proposed", headers=BAD_AUTH)
    assert response.status_code == 401


async def test_admin_disabled_when_token_empty_returns_503(
    client: AsyncClient, monkeypatch
):
    monkeypatch.setattr(cfg.settings, "admin_token", "")
    response = await client.get("/api/admin/careers/proposed", headers=AUTH)
    assert response.status_code == 503
    assert "disabled" in response.json()["error"]["message"].lower()


# ---------------------------------------------------------------------------
# Create career
# ---------------------------------------------------------------------------


async def test_create_career(client: AsyncClient):
    tag = uuid.uuid4().hex[:8]
    response = await client.post("/api/admin/careers", json=_career_payload(tag), headers=AUTH)
    assert response.status_code == 201
    body = response.json()
    assert body["name"].endswith(tag)
    assert body["source"] == "manual"
    assert body["verified"] is True
    assert body["onet_soc_code"] is None


async def test_create_career_llm_proposed_rejected(client: AsyncClient):
    tag = uuid.uuid4().hex[:8]
    payload = {**_career_payload(tag), "source": "llm_proposed"}
    response = await client.post("/api/admin/careers", json=payload, headers=AUTH)
    assert response.status_code == 422


async def test_create_career_duplicate_slug_rejected(client: AsyncClient):
    tag = uuid.uuid4().hex[:8]
    payload = _career_payload(tag)
    first = await client.post("/api/admin/careers", json=payload, headers=AUTH)
    assert first.status_code == 201
    response = await client.post("/api/admin/careers", json=payload, headers=AUTH)
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Update career
# ---------------------------------------------------------------------------


async def test_update_career(client: AsyncClient):
    tag = uuid.uuid4().hex[:8]
    create = await client.post("/api/admin/careers", json=_career_payload(tag), headers=AUTH)
    assert create.status_code == 201
    career_id = create.json()["id"]

    patch = await client.patch(
        f"/api/admin/careers/{career_id}",
        json={"description": "Updated description for quantum computing career research."},
        headers=AUTH,
    )
    assert patch.status_code == 200
    assert patch.json()["description"].startswith("Updated description")


async def test_update_nonexistent_career_returns_404(client: AsyncClient):
    response = await client.patch(
        f"/api/admin/careers/{uuid.uuid4()}",
        json={"description": "Should not matter at all here."},
        headers=AUTH,
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Soft delete
# ---------------------------------------------------------------------------


async def test_delete_career_soft(client: AsyncClient):
    tag = uuid.uuid4().hex[:8]
    payload = _career_payload(tag)
    create = await client.post("/api/admin/careers", json=payload, headers=AUTH)
    assert create.status_code == 201
    career_id = create.json()["id"]
    slug = create.json()["slug"]

    delete = await client.delete(f"/api/admin/careers/{career_id}", headers=AUTH)
    assert delete.status_code == 204

    # Should no longer appear in the public list
    get = await client.get(f"/api/careers/{slug}")
    assert get.status_code == 404


async def test_delete_already_deleted_returns_409(client: AsyncClient):
    tag = uuid.uuid4().hex[:8]
    create = await client.post("/api/admin/careers", json=_career_payload(tag), headers=AUTH)
    assert create.status_code == 201
    career_id = create.json()["id"]
    await client.delete(f"/api/admin/careers/{career_id}", headers=AUTH)
    response = await client.delete(f"/api/admin/careers/{career_id}", headers=AUTH)
    assert response.status_code == 409


async def test_delete_nonexistent_returns_404(client: AsyncClient):
    response = await client.delete(f"/api/admin/careers/{uuid.uuid4()}", headers=AUTH)
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Proposed career listing + verification
# ---------------------------------------------------------------------------


async def test_list_proposed_empty(client: AsyncClient):
    response = await client.get("/api/admin/careers/proposed", headers=AUTH)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_verify_career_flow(client: AsyncClient, db: AsyncSession):
    tag = uuid.uuid4().hex[:8]
    proposed = Career(
        id=uuid.uuid4(),
        name=f"AI Ethics Auditor {tag}",
        slug=f"ai-ethics-auditor-{tag}",
        description="Audit AI systems for bias, fairness, and regulatory compliance.",
        required_skills=["AI Ethics", "Policy Analysis", "Python"],
        optional_skills=["Machine Learning", "Legal Research"],
        personality_fit={
            "openness": 75, "conscientiousness": 80, "extraversion": 50,
            "agreeableness": 72, "neuroticism": 35,
        },
        difficulty="medium",
        growth_potential="high",
        category="Computer & Mathematical",
        source="llm_proposed",
        verified=False,
    )
    db.add(proposed)
    await db.commit()

    # Appears in proposed list
    list_resp = await client.get("/api/admin/careers/proposed", headers=AUTH)
    assert list_resp.status_code == 200
    slugs = [c["slug"] for c in list_resp.json()]
    assert proposed.slug in slugs

    # NOT in public careers list (unverified)
    public_resp = await client.get(f"/api/careers/{proposed.slug}")
    assert public_resp.status_code == 404

    # Verify it
    verify_resp = await client.post(f"/api/admin/careers/{proposed.id}/verify", headers=AUTH)
    assert verify_resp.status_code == 200
    body = verify_resp.json()
    assert body["verified"] is True
    assert body["source"] == "manual"

    # Now appears in the public list
    public_after = await client.get(f"/api/careers/{proposed.slug}")
    assert public_after.status_code == 200

    # No longer in proposed list
    list_after = await client.get("/api/admin/careers/proposed", headers=AUTH)
    slugs_after = [c["slug"] for c in list_after.json()]
    assert proposed.slug not in slugs_after


async def test_verify_non_proposed_returns_409(client: AsyncClient):
    tag = uuid.uuid4().hex[:8]
    create = await client.post("/api/admin/careers", json=_career_payload(tag), headers=AUTH)
    assert create.status_code == 201
    career_id = create.json()["id"]

    response = await client.post(f"/api/admin/careers/{career_id}/verify", headers=AUTH)
    assert response.status_code == 409


async def test_verify_nonexistent_returns_404(client: AsyncClient):
    response = await client.post(f"/api/admin/careers/{uuid.uuid4()}/verify", headers=AUTH)
    assert response.status_code == 404
