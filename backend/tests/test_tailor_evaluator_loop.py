"""Tests for TailorAgent's bounded evaluator-optimizer loop (SPEC 附录 F.5 TASK-C04).

All LLM calls (_tailor, _eval_ats_score) and the deterministic scorer
(_score_deterministically) are mocked — these tests verify the
iteration/stopping/best-version-selection logic, not LLM output quality
or the real ATS simulation pipeline (those are covered elsewhere).
"""
from pathlib import Path
from unittest.mock import MagicMock

from sqlmodel import Session, SQLModel, create_engine, select

from backend.app.agents.tailor import TailorAgent
from backend.app.models.job import Job
from backend.app.models.resume_version import ResumeVersion
from backend.app.models.user_profile import Experience, Preferences, Skill, UserProfile

_TAILOR_RESULT = {
    "summary": "Experienced engineer",
    "selected_skills": ["Kubernetes"],
    "tailored_projects": [{"name": "Proj", "bullets": [{"rewritten": "Did X", "source_raw": "Did X"}]}],
    "changes_summary": "Reworded bullets",
}

_TAILOR_RESULT_WITH_FABRICATED_NUMBER = {
    "summary": "Experienced engineer",
    "selected_skills": ["Kubernetes"],
    "tailored_projects": [
        {"name": "Proj", "bullets": [{"rewritten": "Improved throughput by 50%", "source_raw": "Improved throughput"}]}
    ],
    "changes_summary": "Reworded bullets",
}


def _make_job() -> Job:
    return Job(
        source="manual",
        raw_jd="Looking for a Kubernetes engineer",
        title="Engineer",
        company="Acme",
        skills_required=["Kubernetes"],
        match_score=0.9,
        gap_analysis={
            "strong_matches": [],
            "missing_skills": [],
            "resume_improvements": {"ats_keywords": ["Kubernetes"], "metrics_suggestions": []},
        },
    )


def _make_profile() -> UserProfile:
    return UserProfile(
        name="Jane Doe",
        target_roles=["Software Engineer"],
        skills=[Skill(name="Kubernetes", level="intermediate", years=2.0)],
        experience=[Experience(company="Acme Corp", role="Engineer", duration="2022-2024")],
        projects=[],
        preferences=Preferences(),
    )


def _make_agent(tmp_path, monkeypatch, max_iterations=2, threshold=80.0):
    db_file = tmp_path / "test.db"
    test_engine = create_engine(f"sqlite:///{db_file}", echo=False)
    from backend.app.models import application, job, resume_version  # noqa: F401
    SQLModel.metadata.create_all(test_engine)
    monkeypatch.setattr("backend.app.database.engine", test_engine)

    agent = TailorAgent.__new__(TailorAgent)
    agent.client = MagicMock()
    agent.max_iterations = max_iterations
    agent.deterministic_threshold = threshold
    agent._find_resume_file = MagicMock(return_value=Path("/fake/resume.pdf"))
    agent._eval_ats_score = MagicMock(return_value=70)
    return agent, test_engine


def _count_versions(engine, job_id: str) -> list[ResumeVersion]:
    with Session(engine) as session:
        return list(session.exec(select(ResumeVersion).where(ResumeVersion.job_id == job_id)))


class TestStoppingConditions:
    def test_stops_early_when_threshold_reached_in_first_round(self, tmp_path, monkeypatch):
        agent, engine = _make_agent(tmp_path, monkeypatch, max_iterations=2, threshold=80.0)
        agent._tailor = MagicMock(return_value=_TAILOR_RESULT)
        agent._score_deterministically = MagicMock(return_value=(95.0, {"deterministic_ats_score": 95.0}, []))

        job = _make_job()
        best = agent.run(job, _make_profile())

        assert agent._tailor.call_count == 1
        assert best.deterministic_ats_score == 95.0
        assert len(_count_versions(engine, job.id)) == 1

    def test_stops_when_no_missing_keywords_even_below_threshold(self, tmp_path, monkeypatch):
        agent, engine = _make_agent(tmp_path, monkeypatch, max_iterations=3, threshold=80.0)
        agent._tailor = MagicMock(return_value=_TAILOR_RESULT)
        # Score is well below threshold, but there's nothing to feed back — no point iterating.
        agent._score_deterministically = MagicMock(return_value=(50.0, {}, []))

        job = _make_job()
        agent.run(job, _make_profile())

        assert agent._tailor.call_count == 1

    def test_stops_without_scoring_when_no_uploaded_resume_file(self, tmp_path, monkeypatch):
        agent, engine = _make_agent(tmp_path, monkeypatch, max_iterations=3, threshold=80.0)
        agent._tailor = MagicMock(return_value=_TAILOR_RESULT)
        agent._find_resume_file = MagicMock(return_value=None)
        agent._score_deterministically = MagicMock()

        job = _make_job()
        best = agent.run(job, _make_profile())

        agent._score_deterministically.assert_not_called()
        assert agent._tailor.call_count == 1
        assert best.deterministic_ats_score == 0.0
        assert best.ats_report == {}


class TestIterationAndBestSelection:
    def test_iterates_to_max_and_returns_highest_scoring_round(self, tmp_path, monkeypatch):
        agent, engine = _make_agent(tmp_path, monkeypatch, max_iterations=2, threshold=80.0)
        agent._tailor = MagicMock(return_value=_TAILOR_RESULT)
        agent._score_deterministically = MagicMock(
            side_effect=[
                (60.0, {"round": 1}, ["Kubernetes"]),
                (75.0, {"round": 2}, ["Docker"]),
            ]
        )

        job = _make_job()
        best = agent.run(job, _make_profile())

        assert agent._tailor.call_count == 2
        assert best.deterministic_ats_score == 75.0
        assert len(_count_versions(engine, job.id)) == 2

    def test_returns_first_round_when_later_round_scores_lower(self, tmp_path, monkeypatch):
        """If iteration makes things worse, the best-scoring round must still win — never blindly the last one."""
        agent, engine = _make_agent(tmp_path, monkeypatch, max_iterations=2, threshold=90.0)
        agent._tailor = MagicMock(return_value=_TAILOR_RESULT)
        agent._score_deterministically = MagicMock(
            side_effect=[
                (85.0, {"round": 1}, ["Kubernetes"]),  # below 90 threshold, has feedback -> iterates
                (70.0, {"round": 2}, []),               # worse than round 1
            ]
        )

        job = _make_job()
        best = agent.run(job, _make_profile())

        assert agent._tailor.call_count == 2
        assert best.deterministic_ats_score == 85.0
        assert best.ats_report == {"round": 1}


class TestPersistenceAndValidation:
    def test_every_round_persisted_as_separate_row_not_overwritten(self, tmp_path, monkeypatch):
        agent, engine = _make_agent(tmp_path, monkeypatch, max_iterations=2, threshold=99.0)
        agent._tailor = MagicMock(return_value=_TAILOR_RESULT)
        agent._score_deterministically = MagicMock(
            side_effect=[(50.0, {}, ["Kubernetes"]), (60.0, {}, ["Kubernetes"])]
        )

        job = _make_job()
        agent.run(job, _make_profile())

        versions = _count_versions(engine, job.id)
        assert len(versions) == 2
        assert {v.deterministic_ats_score for v in versions} == {50.0, 60.0}
        assert len({v.id for v in versions}) == 2  # distinct primary keys, no overwrite

    def test_validate_bullets_runs_on_every_round_not_skipped(self, tmp_path, monkeypatch):
        agent, engine = _make_agent(tmp_path, monkeypatch, max_iterations=2, threshold=99.0)
        agent._tailor = MagicMock(return_value=_TAILOR_RESULT_WITH_FABRICATED_NUMBER)
        agent._score_deterministically = MagicMock(
            side_effect=[(50.0, {}, ["Kubernetes"]), (60.0, {}, ["Kubernetes"])]
        )

        job = _make_job()
        agent.run(job, _make_profile())

        versions = _count_versions(engine, job.id)
        assert len(versions) == 2
        for v in versions:
            assert "[VALIDATION WARNINGS]" in v.changes_summary
