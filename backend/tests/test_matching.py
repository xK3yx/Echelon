"""
Unit tests for the rule-based matching engine.

All tests operate on plain Python dicts — no database, no async.
The scoring functions are deterministic: same inputs always produce same outputs.
"""

import pytest

from app.services.matching import (
    EDUCATION_PENALTY_FACTOR,
    CareerData,
    ProfileData,
    ScoredCareer,
    apply_education_penalty,
    compute_interest_score,
    compute_optional_score,
    compute_personality_score,
    compute_skill_score,
    rank_careers,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

NEUTRAL_PERSONALITY = {
    "openness": 50,
    "conscientiousness": 50,
    "extraversion": 50,
    "agreeableness": 50,
    "neuroticism": 50,
}


def _career(**overrides) -> CareerData:
    base: CareerData = {
        "id": "career-1",
        "slug": "software-engineer",
        "name": "Software Engineer",
        "category": "Software Engineering",
        "description": "Build scalable software systems and APIs.",
        "required_skills": ["Python", "SQL", "Git"],
        "optional_skills": ["Docker", "Kubernetes"],
        "personality_fit": NEUTRAL_PERSONALITY.copy(),
        "difficulty": "medium",
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


def _profile(**overrides) -> ProfileData:
    base: ProfileData = {
        "skills": [],
        "interests": [],
        "personality": NEUTRAL_PERSONALITY.copy(),
        "education_level": "bachelors",
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


# ---------------------------------------------------------------------------
# compute_skill_score
# ---------------------------------------------------------------------------


class TestComputeSkillScore:
    def test_full_match(self):
        score = compute_skill_score({"python", "sql", "git"}, ["Python", "SQL", "Git"])
        assert score == pytest.approx(1.0)

    def test_no_match(self):
        score = compute_skill_score({"java", "c++"}, ["Python", "SQL", "Git"])
        assert score == pytest.approx(0.0)

    def test_partial_match(self):
        score = compute_skill_score({"python"}, ["Python", "SQL", "Git"])
        assert score == pytest.approx(1 / 3)

    def test_two_of_three_match(self):
        score = compute_skill_score({"python", "sql"}, ["Python", "SQL", "Git"])
        assert score == pytest.approx(2 / 3)

    def test_case_insensitive(self):
        score = compute_skill_score({"PYTHON", "SQL"}, ["python", "sql", "git"])
        assert score == pytest.approx(2 / 3)

    def test_empty_required_returns_one(self):
        # No requirements means no gaps — perfect score
        score = compute_skill_score({"python"}, [])
        assert score == pytest.approx(1.0)

    def test_extra_skills_do_not_inflate_score(self):
        score = compute_skill_score({"python", "sql", "git", "docker", "rust"}, ["Python", "SQL"])
        assert score == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# compute_optional_score
# ---------------------------------------------------------------------------


class TestComputeOptionalScore:
    def test_full_match_capped_at_0_3(self):
        score = compute_optional_score({"docker", "kubernetes"}, ["Docker", "Kubernetes"])
        assert score == pytest.approx(0.3)

    def test_no_match_is_zero(self):
        score = compute_optional_score({"java"}, ["Docker", "Kubernetes"])
        assert score == pytest.approx(0.0)

    def test_empty_optional_is_zero(self):
        score = compute_optional_score({"python"}, [])
        assert score == pytest.approx(0.0)

    def test_partial_match(self):
        score = compute_optional_score({"docker"}, ["Docker", "Kubernetes"])
        assert score == pytest.approx(0.5 * 0.3)

    def test_score_never_exceeds_0_3(self):
        score = compute_optional_score({"docker", "kubernetes", "redis"}, ["Docker", "Kubernetes"])
        assert score <= 0.3 + 1e-9


# ---------------------------------------------------------------------------
# compute_personality_score
# ---------------------------------------------------------------------------


class TestComputePersonalityScore:
    def test_perfect_match_is_one(self):
        score = compute_personality_score(NEUTRAL_PERSONALITY, NEUTRAL_PERSONALITY)
        assert score == pytest.approx(1.0)

    def test_maximum_deviation_is_zero(self):
        user = {k: 0 for k in NEUTRAL_PERSONALITY}
        ideal = {k: 100 for k in NEUTRAL_PERSONALITY}
        score = compute_personality_score(user, ideal)
        assert score == pytest.approx(0.0)

    def test_partial_deviation(self):
        user = {k: 50 for k in NEUTRAL_PERSONALITY}
        ideal = {k: 100 for k in NEUTRAL_PERSONALITY}
        # mean diff = 50, score = 1 - 50/100 = 0.5
        score = compute_personality_score(user, ideal)
        assert score == pytest.approx(0.5)

    def test_single_trait_deviation(self):
        user = {**NEUTRAL_PERSONALITY, "openness": 0}
        ideal = NEUTRAL_PERSONALITY.copy()
        # mean diff = 50/5 = 10, score = 1 - 10/100 = 0.9
        score = compute_personality_score(user, ideal)
        assert score == pytest.approx(0.9)

    def test_score_bounded_zero_to_one(self):
        user = {k: 0 for k in NEUTRAL_PERSONALITY}
        ideal = {k: 100 for k in NEUTRAL_PERSONALITY}
        score = compute_personality_score(user, ideal)
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# compute_interest_score
# ---------------------------------------------------------------------------


class TestComputeInterestScore:
    def test_all_interests_match(self):
        career = _career(
            name="Software Engineer",
            category="Software Engineering",
            description="Build scalable software systems.",
        )
        score = compute_interest_score(["software", "engineering"], career)
        assert score == pytest.approx(1.0)

    def test_no_interests_match(self):
        career = _career(
            name="Software Engineer",
            category="Software Engineering",
            description="Build scalable software systems.",
        )
        score = compute_interest_score(["medicine", "cooking"], career)
        assert score == pytest.approx(0.0)

    def test_partial_match(self):
        career = _career(
            name="Data Scientist",
            category="Data & Analytics",
            description="Analyse datasets and build models.",
        )
        # "data" is present; "cooking" is not
        score = compute_interest_score(["data", "cooking"], career)
        assert score == pytest.approx(0.5)

    def test_empty_interests_is_zero(self):
        score = compute_interest_score([], _career())
        assert score == pytest.approx(0.0)

    def test_case_insensitive_match(self):
        career = _career(
            name="Software Engineer",
            category="Software Engineering",
            description="Build scalable systems.",
        )
        score = compute_interest_score(["SOFTWARE"], career)
        assert score == pytest.approx(1.0)

    def test_substring_match(self):
        career = _career(
            name="Data Scientist",
            category="Data & Analytics",
            description="Work with large datasets.",
        )
        # "data" should appear as a substring in "datasets"
        score = compute_interest_score(["data"], career)
        assert score == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# rank_careers
# ---------------------------------------------------------------------------


class TestRankCareers:
    def _make_careers(self, n: int) -> list[CareerData]:
        """Generate n distinct careers with incrementally better skill match."""
        careers = []
        for i in range(n):
            careers.append(
                _career(
                    id=f"career-{i}",
                    slug=f"career-{i}",
                    name=f"Career {i}",
                    required_skills=["Python"] * (i + 1),  # more required = harder to match
                )
            )
        return careers

    def test_returns_at_most_ten(self):
        careers = self._make_careers(15)
        profile = _profile(skills=["Python"])
        result = rank_careers(profile, careers)
        assert len(result) <= 10

    def test_returns_all_when_fewer_than_ten(self):
        careers = self._make_careers(5)
        profile = _profile(skills=["Python"])
        result = rank_careers(profile, careers)
        assert len(result) == 5

    def test_sorted_descending_by_total_score(self):
        careers = self._make_careers(10)
        profile = _profile(skills=["Python"])
        result = rank_careers(profile, careers)
        scores = [r.total_score for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_empty_careers_returns_empty(self):
        result = rank_careers(_profile(), [])
        assert result == []

    def test_result_type_is_scored_career(self):
        result = rank_careers(_profile(skills=["Python"]), [_career()])
        assert all(isinstance(r, ScoredCareer) for r in result)

    def test_perfect_skill_match_ranks_above_no_match(self):
        perfect = _career(
            id="perfect", slug="perfect", name="Perfect", required_skills=["Python"]
        )
        zero = _career(
            id="zero", slug="zero", name="Zero", required_skills=["COBOL"]
        )
        profile = _profile(skills=["Python"], personality=NEUTRAL_PERSONALITY)
        result = rank_careers(profile, [zero, perfect])
        assert result[0].slug == "perfect"

    def test_all_sub_scores_in_expected_range(self):
        careers = self._make_careers(5)
        profile = _profile(skills=["Python"], interests=["engineering"])
        result = rank_careers(profile, careers)
        for r in result:
            assert 0.0 <= r.skill_score <= 1.0
            assert 0.0 <= r.optional_score <= 0.3 + 1e-9
            assert 0.0 <= r.personality_score <= 1.0
            assert 0.0 <= r.interest_score <= 1.0
            assert 0.0 <= r.total_score

    def test_total_score_matches_weighted_formula(self):
        career = _career(required_skills=["Python"], optional_skills=[])
        profile = _profile(skills=["Python"], interests=[], personality=NEUTRAL_PERSONALITY)
        result = rank_careers(profile, [career])
        r = result[0]
        expected = (
            0.45 * r.skill_score
            + 0.15 * r.optional_score
            + 0.25 * r.personality_score
            + 0.15 * r.interest_score
        )
        assert r.total_score == pytest.approx(expected, abs=1e-5)

    def test_duplicate_careers_handled_without_error(self):
        career = _career()
        result = rank_careers(_profile(skills=["Python"]), [career, career])
        assert len(result) == 2


# ---------------------------------------------------------------------------
# apply_education_penalty
# ---------------------------------------------------------------------------


class TestApplyEducationPenalty:
    def test_no_penalty_for_bachelors_and_high_difficulty(self):
        result = apply_education_penalty(0.8, "bachelors", "high")
        assert result == pytest.approx(0.8)

    def test_penalty_applied_for_high_school_and_high_difficulty(self):
        result = apply_education_penalty(0.8, "high_school", "high")
        assert result == pytest.approx(0.8 * EDUCATION_PENALTY_FACTOR)

    def test_no_penalty_for_high_school_and_medium_difficulty(self):
        result = apply_education_penalty(0.8, "high_school", "medium")
        assert result == pytest.approx(0.8)

    def test_no_penalty_for_high_school_and_low_difficulty(self):
        result = apply_education_penalty(0.8, "high_school", "low")
        assert result == pytest.approx(0.8)

    def test_no_penalty_for_empty_education_level(self):
        result = apply_education_penalty(0.8, "", "high")
        assert result == pytest.approx(0.8)

    def test_penalty_factor_value(self):
        assert EDUCATION_PENALTY_FACTOR == pytest.approx(0.7)

    def test_rank_careers_applies_education_penalty(self):
        high_career = _career(
            id="high-1", slug="high-career", name="High Career", difficulty="high"
        )
        profile_hs = _profile(skills=["Python", "SQL", "Git"], education_level="high_school")
        profile_ba = _profile(skills=["Python", "SQL", "Git"], education_level="bachelors")

        result_hs = rank_careers(profile_hs, [high_career])
        result_ba = rank_careers(profile_ba, [high_career])

        assert result_hs[0].total_score == pytest.approx(
            result_ba[0].total_score * EDUCATION_PENALTY_FACTOR, abs=1e-5
        )

    def test_penalty_does_not_filter_career_out(self):
        high_career = _career(difficulty="high")
        profile_hs = _profile(education_level="high_school")
        result = rank_careers(profile_hs, [high_career])
        assert len(result) == 1
