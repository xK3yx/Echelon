import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career import Career

# ---------------------------------------------------------------------------
# Shared payload helpers
# ---------------------------------------------------------------------------

VALID_PROFILE = {
    "skills": ["Python", "SQL"],
    "interests": ["technology", "data"],
    "education_level": "bachelors",
    "personality": {
        "openness": 70,
        "conscientiousness": 80,
        "extraversion": 40,
        "agreeableness": 60,
        "neuroticism": 30,
    },
    "constraints": None,
}


def _career_fixture(suffix: str) -> Career:
    return Career(
        id=uuid.uuid4(),
        name=f"Test Career {suffix}",
        slug=f"test-career-{suffix}",
        description="A career used in tests.",
        required_skills=["Python"],
        optional_skills=["Docker"],
        personality_fit={
            "openness": 65,
            "conscientiousness": 80,
            "extraversion": 35,
            "agreeableness": 55,
            "neuroticism": 30,
        },
        difficulty="medium",
        growth_potential="high",
        category="Software Engineering",
        source="manual",
        verified=True,
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


async def test_health(client: AsyncClient):
    response = await client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "2.1.0"


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------


async def test_create_profile(client: AsyncClient):
    response = await client.post("/api/profiles", json=VALID_PROFILE)
    assert response.status_code == 201
    body = response.json()
    assert "id" in body
    assert "user_id" in body
    assert body["skills"] == ["Python", "SQL"]
    assert body["education_level"] == "bachelors"
    assert body["personality"]["openness"] == 70


async def test_get_profile(client: AsyncClient):
    create = await client.post("/api/profiles", json=VALID_PROFILE)
    assert create.status_code == 201
    profile_id = create.json()["id"]

    get = await client.get(f"/api/profiles/{profile_id}")
    assert get.status_code == 200
    assert get.json()["id"] == profile_id


async def test_get_profile_not_found(client: AsyncClient):
    response = await client.get(f"/api/profiles/{uuid.uuid4()}")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"


async def test_create_profile_empty_skills_rejected(client: AsyncClient):
    payload = {**VALID_PROFILE, "skills": []}
    response = await client.post("/api/profiles", json=payload)
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


async def test_create_profile_invalid_education_rejected(client: AsyncClient):
    payload = {**VALID_PROFILE, "education_level": "kindergarten"}
    response = await client.post("/api/profiles", json=payload)
    assert response.status_code == 422


async def test_create_profile_personality_out_of_range_rejected(client: AsyncClient):
    payload = {
        **VALID_PROFILE,
        "personality": {**VALID_PROFILE["personality"], "openness": 150},
    }
    response = await client.post("/api/profiles", json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Careers
# ---------------------------------------------------------------------------


async def test_list_careers(client: AsyncClient, db: AsyncSession):
    tag = uuid.uuid4().hex[:8]
    career = _career_fixture(tag)
    db.add(career)
    await db.commit()

    response = await client.get("/api/careers")
    assert response.status_code == 200
    slugs = [c["slug"] for c in response.json()]
    assert f"test-career-{tag}" in slugs

    await db.delete(career)
    await db.commit()


async def test_get_career_by_slug(client: AsyncClient, db: AsyncSession):
    tag = uuid.uuid4().hex[:8]
    career = _career_fixture(tag)
    db.add(career)
    await db.commit()

    response = await client.get(f"/api/careers/test-career-{tag}")
    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == f"test-career-{tag}"
    assert body["difficulty"] == "medium"
    assert body["growth_potential"] == "high"
    assert isinstance(body["required_skills"], list)
    assert body["source"] == "manual"
    assert body["verified"] is True
    assert body["onet_soc_code"] is None
    assert body["external_url"] is None

    await db.delete(career)
    await db.commit()


async def test_get_career_not_found(client: AsyncClient):
    response = await client.get("/api/careers/this-career-does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# Recommendations — error-path smoke tests (no real Groq call needed)
# ---------------------------------------------------------------------------


async def test_recommendation_profile_not_found(client: AsyncClient):
    payload = {"profile_id": str(uuid.uuid4()), "refresh": False}
    response = await client.post("/api/recommendations", json=payload)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


async def test_recommendation_missing_groq_key_returns_502(
    client: AsyncClient, db: AsyncSession, monkeypatch
):
    """When GROQ_API_KEY is empty the pipeline raises GroqError; expect 502."""
    import app.config as cfg

    monkeypatch.setattr(cfg.settings, "groq_api_key", "")

    # Create a real profile + seed one career so Stage 1 has data
    tag = uuid.uuid4().hex[:8]
    career = _career_fixture(tag)
    db.add(career)
    await db.commit()

    create = await client.post("/api/profiles", json=VALID_PROFILE)
    assert create.status_code == 201
    profile_id = create.json()["id"]

    response = await client.post(
        "/api/recommendations", json={"profile_id": profile_id, "refresh": True}
    )
    assert response.status_code == 502

    await db.delete(career)
    await db.commit()


async def test_get_recommendation_not_found(client: AsyncClient):
    response = await client.get(f"/api/recommendations/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
