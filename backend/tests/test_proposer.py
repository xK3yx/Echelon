"""
Tests for the Stage 2.5 LLM career proposal flow.

All tests mock the Groq client — no real API calls made.
Covers:
  - Proposal triggered when top rule score < threshold
  - Proposal NOT triggered when top score >= threshold
  - Proposal NOT triggered when allow_proposed=False
  - Proposed careers persisted with correct DB flags
  - Response shape always includes proposed_careers (possibly empty)
  - Name-deduplication: proposed career matching an existing name is dropped
  - Proposal skipped gracefully on LLM validation failure
"""
import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.config as cfg
from app.models.career import Career

# ---------------------------------------------------------------------------
# Shared helpers
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

_PROPOSAL_RESPONSE = {
    "proposed_careers": [
        {
            "name": "Synthetic Data Engineer",
            "description": (
                "Design and generate high-quality synthetic datasets for ML pipelines. "
                "Works at the intersection of data engineering and privacy compliance."
            ),
            "category": "Computer & Mathematical",
            "required_skills": ["Python", "Data Generation", "Privacy Engineering", "SQL", "ML Pipelines"],
            "optional_skills": ["Differential Privacy", "GANs"],
            "personality_fit": {
                "openness": 72, "conscientiousness": 78, "extraversion": 38,
                "agreeableness": 58, "neuroticism": 32,
            },
            "difficulty": "medium",
            "growth_potential": "high",
            "rationale": (
                "The user's Python and SQL skills directly map to this role, and their "
                "interest in data aligns with the synthetic data generation focus."
            ),
        }
    ]
}


def _mock_groq_response(payload: dict):
    """Return an AsyncMock that simulates a Groq chat_completion response."""
    mock = AsyncMock(return_value={
        "choices": [{"message": {"content": json.dumps(payload)}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 200},
    })
    return mock


def _career_fixture(suffix: str, *, source: str = "manual", verified: bool = True) -> Career:
    return Career(
        id=uuid.uuid4(),
        name=f"Test Career {suffix}",
        slug=f"test-career-{suffix}",
        description="A career used in tests.",
        required_skills=["COBOL"],  # no overlap with VALID_PROFILE skills
        optional_skills=[],
        personality_fit={
            "openness": 50, "conscientiousness": 50, "extraversion": 50,
            "agreeableness": 50, "neuroticism": 50,
        },
        difficulty="medium",
        growth_potential="medium",
        category="Other",
        source=source,
        verified=verified,
    )


# ---------------------------------------------------------------------------
# Unit-level tests for services/proposer.py
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_proposal_returns_career_dicts(monkeypatch):
    """proposer.run_proposal returns validated dicts when the LLM responds correctly."""
    import app.services.proposer as proposer_mod

    monkeypatch.setattr(proposer_mod.groq, "chat_completion", _mock_groq_response(_PROPOSAL_RESPONSE))

    from app.services.proposer import run_proposal

    result = await run_proposal(
        profile={"skills": ["Python"], "interests": ["data"], "personality": {
            "openness": 70, "conscientiousness": 80, "extraversion": 40,
            "agreeableness": 60, "neuroticism": 30,
        }},
        top_career_names=["Data Scientist"],
        existing_names={"Data Scientist"},
        model="llama-3.3-70b-versatile",
    )

    assert len(result) == 1
    assert result[0]["name"] == "Synthetic Data Engineer"
    assert result[0]["source"] == "llm_proposed"
    assert result[0]["verified"] is False
    assert result[0]["slug"].startswith("proposed-")
    assert "rationale" in result[0]


@pytest.mark.asyncio
async def test_run_proposal_deduplicates_existing_names(monkeypatch):
    """A proposed career whose name matches an existing career is silently dropped."""
    import app.services.proposer as proposer_mod

    # Existing names contains the proposed career name
    existing = {"Synthetic Data Engineer", "Data Scientist"}
    monkeypatch.setattr(proposer_mod.groq, "chat_completion", _mock_groq_response(_PROPOSAL_RESPONSE))

    from app.services.proposer import run_proposal

    result = await run_proposal(
        profile={"skills": [], "interests": [], "personality": {
            "openness": 50, "conscientiousness": 50, "extraversion": 50,
            "agreeableness": 50, "neuroticism": 50,
        }},
        top_career_names=[],
        existing_names=existing,
        model="llama-3.3-70b-versatile",
    )
    assert result == []


@pytest.mark.asyncio
async def test_run_proposal_returns_empty_on_validation_failure(monkeypatch):
    """On two consecutive validation failures, run_proposal returns [] without raising."""
    import app.services.proposer as proposer_mod

    bad_mock = AsyncMock(return_value={
        "choices": [{"message": {"content": '{"not_the_right_key": []}'}}],
        "usage": {},
    })
    monkeypatch.setattr(proposer_mod.groq, "chat_completion", bad_mock)

    from app.services.proposer import run_proposal

    result = await run_proposal(
        profile={"skills": [], "interests": [], "personality": {
            "openness": 50, "conscientiousness": 50, "extraversion": 50,
            "agreeableness": 50, "neuroticism": 50,
        }},
        top_career_names=[],
        existing_names=set(),
        model="llama-3.3-70b-versatile",
    )
    assert result == []


# ---------------------------------------------------------------------------
# Integration-level tests through the /api/recommendations endpoint
# ---------------------------------------------------------------------------


@pytest.fixture
def set_low_threshold(monkeypatch):
    """Force propose_threshold to 1.0 so it always triggers."""
    monkeypatch.setattr(cfg.settings, "propose_threshold", 1.0)


@pytest.fixture
def set_high_threshold(monkeypatch):
    """Force propose_threshold to 0.0 so it never triggers."""
    monkeypatch.setattr(cfg.settings, "propose_threshold", 0.0)


async def test_proposed_careers_in_response_shape(client: AsyncClient, db: AsyncSession):
    """Response always contains a proposed_careers key (even if empty)."""
    tag = uuid.uuid4().hex[:8]
    career = _career_fixture(tag)
    db.add(career)
    await db.commit()

    create = await client.post("/api/profiles", json=VALID_PROFILE)
    profile_id = create.json()["id"]

    with patch("app.routers.recommendations.run_ranking") as mock_rank, \
         patch("app.routers.recommendations.run_gap_roadmap") as mock_gap:

        # Stub ranking output (model_construct bypasses min_length=5 for test use)
        from app.llm.validators import (
            CareerGapRoadmap,
            GapRoadmapOutput,
            RankedCareerItem,
            RankingOutput,
            RoadmapPhase,
        )
        from app.services.matching import ScoredCareer

        ranked_item = RankedCareerItem.model_construct(
            slug=f"test-career-{tag}",
            fit_reasoning="Good fit because of matching skills and interests.",
            strengths=["Skill alignment"],
            risks=["Limited growth"],
            confidence=70,
        )
        mock_rank.return_value = (
            RankingOutput.model_construct(ranked_careers=[ranked_item]),
            [ScoredCareer(
                career_id=str(career.id), slug=f"test-career-{tag}",
                name=career.name, category=career.category,
                total_score=0.5, skill_score=0.5, optional_score=0.0,
                personality_score=0.8, interest_score=0.3,
            )],
        )
        mock_gap.return_value = GapRoadmapOutput(careers=[
            CareerGapRoadmap(
                slug=f"test-career-{tag}",
                skill_gaps=[],
                roadmap=[
                    RoadmapPhase(phase="Beginner", skills=["Skill A"], projects=["P1", "P2"], duration_weeks=8),
                    RoadmapPhase(phase="Intermediate", skills=["Skill B"], projects=["P3", "P4"], duration_weeks=12),
                    RoadmapPhase(phase="Advanced", skills=["Skill C"], projects=["P5", "P6"], duration_weeks=16),
                ],
            )
        ])

        response = await client.post(
            "/api/recommendations",
            json={"profile_id": profile_id, "refresh": True, "allow_proposed": False},
        )

    assert response.status_code == 201
    body = response.json()
    assert "proposed_careers" in body["result"]
    assert isinstance(body["result"]["proposed_careers"], list)


async def test_proposal_not_triggered_when_allow_proposed_false(
    client: AsyncClient, db: AsyncSession, set_low_threshold
):
    """allow_proposed=False must prevent any proposal call."""
    tag = uuid.uuid4().hex[:8]
    career = _career_fixture(tag)
    db.add(career)
    await db.commit()

    create = await client.post("/api/profiles", json=VALID_PROFILE)
    profile_id = create.json()["id"]

    with patch("app.routers.recommendations.run_ranking") as mock_rank, \
         patch("app.routers.recommendations.run_gap_roadmap") as mock_gap, \
         patch("app.routers.recommendations.run_proposal") as mock_propose:

        _stub_ranking(mock_rank, mock_gap, career, tag)
        mock_propose.return_value = []

        response = await client.post(
            "/api/recommendations",
            json={"profile_id": profile_id, "refresh": True, "allow_proposed": False},
        )

    assert response.status_code == 201
    mock_propose.assert_not_called()


async def test_proposal_triggered_when_score_below_threshold(
    client: AsyncClient, db: AsyncSession, set_low_threshold
):
    """Proposal IS called when top_score < threshold."""
    tag = uuid.uuid4().hex[:8]
    career = _career_fixture(tag)
    db.add(career)
    await db.commit()

    create = await client.post("/api/profiles", json=VALID_PROFILE)
    profile_id = create.json()["id"]

    with patch("app.routers.recommendations.run_ranking") as mock_rank, \
         patch("app.routers.recommendations.run_gap_roadmap") as mock_gap, \
         patch("app.routers.recommendations.run_proposal") as mock_propose:

        _stub_ranking(mock_rank, mock_gap, career, tag)
        mock_propose.return_value = []  # no proposals actually created

        response = await client.post(
            "/api/recommendations",
            json={"profile_id": profile_id, "refresh": True, "allow_proposed": True},
        )

    assert response.status_code == 201
    mock_propose.assert_called_once()


async def test_proposal_not_triggered_when_score_above_threshold(
    client: AsyncClient, db: AsyncSession, set_high_threshold
):
    """Proposal is NOT called when top_score >= threshold (high threshold = never triggers)."""
    tag = uuid.uuid4().hex[:8]
    career = _career_fixture(tag)
    db.add(career)
    await db.commit()

    create = await client.post("/api/profiles", json=VALID_PROFILE)
    profile_id = create.json()["id"]

    with patch("app.routers.recommendations.run_ranking") as mock_rank, \
         patch("app.routers.recommendations.run_gap_roadmap") as mock_gap, \
         patch("app.routers.recommendations.run_proposal") as mock_propose:

        _stub_ranking(mock_rank, mock_gap, career, tag)
        mock_propose.return_value = []

        response = await client.post(
            "/api/recommendations",
            json={"profile_id": profile_id, "refresh": True, "allow_proposed": True},
        )

    assert response.status_code == 201
    mock_propose.assert_not_called()


async def test_proposed_career_persisted_with_correct_flags(
    client: AsyncClient, db: AsyncSession, set_low_threshold
):
    """When a proposal is returned, it is persisted as llm_proposed + unverified."""
    tag = uuid.uuid4().hex[:8]
    career = _career_fixture(tag)
    db.add(career)
    await db.commit()

    create = await client.post("/api/profiles", json=VALID_PROFILE)
    profile_id = create.json()["id"]

    proposal_record = {
        "id": uuid.uuid4(),
        "name": f"Neuro-Interface Designer {tag}",
        "slug": f"proposed-{uuid.uuid4().hex[:8]}",
        "description": "Design brain-computer interfaces for assistive technology and consumer devices.",
        "required_skills": ["Neuroscience", "Python", "Signal Processing", "UX Design", "ML"],
        "optional_skills": ["C++"],
        "personality_fit": {
            "openness": 80, "conscientiousness": 70, "extraversion": 45,
            "agreeableness": 65, "neuroticism": 35,
        },
        "difficulty": "high",
        "growth_potential": "high",
        "category": "Computer & Mathematical",
        "source": "llm_proposed",
        "verified": False,
        "rationale": "Great match given user's Python skills and interest in technology.",
    }

    with patch("app.routers.recommendations.run_ranking") as mock_rank, \
         patch("app.routers.recommendations.run_gap_roadmap") as mock_gap, \
         patch("app.routers.recommendations.run_proposal") as mock_propose:

        _stub_ranking(mock_rank, mock_gap, career, tag)
        mock_propose.return_value = [proposal_record]

        response = await client.post(
            "/api/recommendations",
            json={"profile_id": profile_id, "refresh": True, "allow_proposed": True},
        )

    assert response.status_code == 201
    result = response.json()["result"]
    assert len(result["proposed_careers"]) == 1
    pc = result["proposed_careers"][0]
    assert pc["source"] == "llm_proposed"
    assert pc["verified"] is False
    assert "rationale" in pc

    # Confirm the career row was persisted in the DB
    db_row = await db.execute(
        select(Career).where(Career.name == proposal_record["name"])
    )
    saved = db_row.scalar_one_or_none()
    assert saved is not None
    assert saved.source == "llm_proposed"
    assert saved.verified is False
    assert saved.proposed_for_profile_id == uuid.UUID(profile_id)


# ---------------------------------------------------------------------------
# Shared stub helper
# ---------------------------------------------------------------------------


def _stub_ranking(mock_rank, mock_gap, career: Career, tag: str) -> None:
    from app.llm.validators import (
        CareerGapRoadmap,
        GapRoadmapOutput,
        RankedCareerItem,
        RankingOutput,
        RoadmapPhase,
    )
    from app.services.matching import ScoredCareer

    ranked_item = RankedCareerItem.model_construct(
        slug=f"test-career-{tag}",
        fit_reasoning="Good fit because of matching skills and interests.",
        strengths=["Skill alignment"],
        risks=["Limited growth"],
        confidence=70,
    )
    # model_construct bypasses the min_length=5 constraint — valid for test stubs
    mock_rank.return_value = (
        RankingOutput.model_construct(ranked_careers=[ranked_item]),
        [ScoredCareer(
            career_id=str(career.id), slug=f"test-career-{tag}",
            name=career.name, category=career.category,
            total_score=0.1, skill_score=0.1, optional_score=0.0,
            personality_score=0.5, interest_score=0.1,
        )],
    )
    mock_gap.return_value = GapRoadmapOutput(careers=[
        CareerGapRoadmap(
            slug=f"test-career-{tag}",
            skill_gaps=[],
            roadmap=[
                RoadmapPhase(phase="Beginner", skills=["A"], projects=["P1", "P2"], duration_weeks=8),
                RoadmapPhase(phase="Intermediate", skills=["B"], projects=["P3", "P4"], duration_weeks=12),
                RoadmapPhase(phase="Advanced", skills=["C"], projects=["P5", "P6"], duration_weeks=16),
            ],
        )
    ])
