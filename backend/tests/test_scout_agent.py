"""Tests for ScoutAgent auto-filter logic (mocked LLM calls)."""
import pytest
from unittest.mock import patch, MagicMock
from backend.app.models.job import Job, JobStatus
from backend.app.models.user_profile import UserProfile, Skill, Experience, Project, Preferences


def make_profile():
    return UserProfile(
        name="Test User",
        target_roles=["Data Scientist"],
        skills=[Skill(name="Python", level="expert", years=5.0)],
        experience=[],
        projects=[],
        preferences=Preferences(locations=["Sydney"]),
    )


def _make_scout_with_mocked_calls(score: float, parse_result: dict | None = None):
    """Create a ScoutAgent with mocked _parse_jd and _evaluate methods."""
    from backend.app.agents.scout import ScoutAgent

    agent = ScoutAgent.__new__(ScoutAgent)
    agent.client = MagicMock()

    default_parse = {
        "title": "Data Scientist",
        "company": "TestCorp",
        "location": "Sydney",
        "salary_range": "$100k",
        "skills_required": ["Python", "SQL"],
    }

    eval_result = {
        "ats_pct": int(round(score * 100)),
        "strong_matches": ["Python", "ML"],
        "missing_skills": ["Kubernetes"],
        "unmet_requirements": [],
        "notes": "Good match",
        "skills_improvements": {"technical": [], "certifications": [], "soft_skills": [], "tools": []},
        "resume_improvements": {"bullet_strength": [], "achievements_feedback": "", "metrics_suggestions": [], "ats_keywords": []},
        "formatting_improvements": {"tone_clarity": [], "action_verbs": [], "layout": []},
        "recommendations": {"top_5": [], "quick_wins": [], "deeper_improvements": [], "estimated_improvement_pct": 0},
    }

    agent._parse_jd = MagicMock(return_value=parse_result or default_parse)
    agent._evaluate = MagicMock(return_value=eval_result)
    return agent


class TestScoutAgentAutoFilter:
    def test_low_score_discarded_with_auto_filter(self, tmp_path, monkeypatch):
        """Jobs with score < 0.70 should be discarded when auto_filter=True."""
        db_file = tmp_path / "test.db"
        from sqlmodel import create_engine, SQLModel
        test_engine = create_engine(f"sqlite:///{db_file}", echo=False)
        from backend.app.models import job, application, resume_version
        SQLModel.metadata.create_all(test_engine)
        monkeypatch.setattr("backend.app.database.engine", test_engine)
        monkeypatch.setattr("backend.app.config.MID_SCORE_THRESHOLD", 0.70)

        agent = _make_scout_with_mocked_calls(score=0.50)
        profile = make_profile()

        result = agent.run(
            raw_jd="Python Developer needed",
            user_profile=profile,
            source="seek",
            auto_filter=True,
            notify=False,
        )
        assert result is None

    def test_low_score_saved_without_auto_filter(self, tmp_path, monkeypatch):
        """Jobs with low score should be saved when auto_filter=False."""
        db_file = tmp_path / "test.db"
        from sqlmodel import create_engine, SQLModel
        test_engine = create_engine(f"sqlite:///{db_file}", echo=False)
        from backend.app.models import job, application, resume_version
        SQLModel.metadata.create_all(test_engine)
        monkeypatch.setattr("backend.app.database.engine", test_engine)

        agent = _make_scout_with_mocked_calls(score=0.50)
        profile = make_profile()

        result = agent.run(
            raw_jd="Python Developer needed",
            user_profile=profile,
            source="manual",
            auto_filter=False,
            notify=False,
        )
        assert result is not None
        assert isinstance(result, Job)
        assert result.match_score == 0.50

    def test_high_score_job_saved(self, tmp_path, monkeypatch):
        """Jobs with score >= 0.80 should be saved."""
        db_file = tmp_path / "test.db"
        from sqlmodel import create_engine, SQLModel
        test_engine = create_engine(f"sqlite:///{db_file}", echo=False)
        from backend.app.models import job, application, resume_version
        SQLModel.metadata.create_all(test_engine)
        monkeypatch.setattr("backend.app.database.engine", test_engine)
        monkeypatch.setattr("backend.app.config.HIGH_SCORE_THRESHOLD", 0.80)
        monkeypatch.setattr("backend.app.config.MID_SCORE_THRESHOLD", 0.70)

        # Disable notification push
        monkeypatch.setattr("backend.app.notifications.NOTIFICATION_WEBHOOK_URL", "")

        agent = _make_scout_with_mocked_calls(score=0.85)
        profile = make_profile()

        result = agent.run(
            raw_jd="Senior Data Scientist",
            user_profile=profile,
            source="seek",
            auto_filter=True,
            notify=True,
        )
        assert result is not None
        assert result.match_score == 0.85

    def test_mid_score_job_saved(self, tmp_path, monkeypatch):
        """Jobs with score between 0.70 and 0.80 should be saved."""
        db_file = tmp_path / "test.db"
        from sqlmodel import create_engine, SQLModel
        test_engine = create_engine(f"sqlite:///{db_file}", echo=False)
        from backend.app.models import job, application, resume_version
        SQLModel.metadata.create_all(test_engine)
        monkeypatch.setattr("backend.app.database.engine", test_engine)
        monkeypatch.setattr("backend.app.config.MID_SCORE_THRESHOLD", 0.70)

        agent = _make_scout_with_mocked_calls(score=0.75)
        profile = make_profile()

        result = agent.run(
            raw_jd="Data Scientist role",
            user_profile=profile,
            source="indeed",
            auto_filter=True,
            notify=False,
        )
        assert result is not None
        assert result.match_score == 0.75
        assert result.status == JobStatus.new

    def test_run_with_prepopulated_title_company(self, tmp_path, monkeypatch):
        """When title+company provided, only skills should be parsed."""
        db_file = tmp_path / "test.db"
        from sqlmodel import create_engine, SQLModel
        test_engine = create_engine(f"sqlite:///{db_file}", echo=False)
        from backend.app.models import job, application, resume_version
        SQLModel.metadata.create_all(test_engine)
        monkeypatch.setattr("backend.app.database.engine", test_engine)
        monkeypatch.setattr("backend.app.config.MID_SCORE_THRESHOLD", 0.70)

        agent = _make_scout_with_mocked_calls(score=0.80)
        profile = make_profile()

        result = agent.run(
            raw_jd="Data scientist role needing Python and SQL",
            user_profile=profile,
            source="seek",
            source_url="https://seek.com.au/job/999",
            title="Data Scientist",
            company="Google",
            location="Sydney",
            salary_range="$150k",
            auto_filter=True,
            notify=False,
        )
        assert result is not None
        assert result.title == "Data Scientist"
        assert result.company == "Google"
        assert result.source_url == "https://seek.com.au/job/999"

    def test_job_persisted_in_database(self, tmp_path, monkeypatch):
        """Saved job should be retrievable from database."""
        db_file = tmp_path / "test_persist.db"
        from sqlmodel import create_engine, SQLModel, Session
        test_engine = create_engine(f"sqlite:///{db_file}", echo=False)
        from backend.app.models import job, application, resume_version
        SQLModel.metadata.create_all(test_engine)
        monkeypatch.setattr("backend.app.database.engine", test_engine)
        monkeypatch.setattr("backend.app.config.MID_SCORE_THRESHOLD", 0.70)

        agent = _make_scout_with_mocked_calls(score=0.80)
        profile = make_profile()

        result = agent.run(
            raw_jd="Senior Data Scientist role",
            user_profile=profile,
            source="seek",
            auto_filter=True,
            notify=False,
        )
        assert result is not None
        job_id = result.id

        # Verify job is in the database
        from backend.app.models.job import Job as JobModel
        with Session(test_engine) as session:
            fetched = session.get(JobModel, job_id)
            assert fetched is not None
            assert fetched.match_score == 0.80

    def test_gap_analysis_stored_correctly(self, tmp_path, monkeypatch):
        """Gap analysis data should be stored in the job record."""
        db_file = tmp_path / "test_gap.db"
        from sqlmodel import create_engine, SQLModel
        test_engine = create_engine(f"sqlite:///{db_file}", echo=False)
        from backend.app.models import job, application, resume_version
        SQLModel.metadata.create_all(test_engine)
        monkeypatch.setattr("backend.app.database.engine", test_engine)
        monkeypatch.setattr("backend.app.config.MID_SCORE_THRESHOLD", 0.70)

        agent = _make_scout_with_mocked_calls(score=0.75)
        profile = make_profile()

        result = agent.run(
            raw_jd="Data Scientist role",
            user_profile=profile,
            source="indeed",
            auto_filter=True,
            notify=False,
        )
        assert result is not None
        assert "strong_matches" in result.gap_analysis
        assert "missing_skills" in result.gap_analysis
        assert "Python" in result.gap_analysis["strong_matches"]

    def test_source_url_stored_in_job(self, tmp_path, monkeypatch):
        """Source URL should be stored in the saved job."""
        db_file = tmp_path / "test_url.db"
        from sqlmodel import create_engine, SQLModel
        test_engine = create_engine(f"sqlite:///{db_file}", echo=False)
        from backend.app.models import job, application, resume_version
        SQLModel.metadata.create_all(test_engine)
        monkeypatch.setattr("backend.app.database.engine", test_engine)
        monkeypatch.setattr("backend.app.config.MID_SCORE_THRESHOLD", 0.70)

        agent = _make_scout_with_mocked_calls(score=0.80)
        profile = make_profile()

        result = agent.run(
            raw_jd="Data Scientist role",
            user_profile=profile,
            source="linkedin",
            source_url="https://linkedin.com/jobs/view/123",
            auto_filter=True,
            notify=False,
        )
        assert result is not None
        assert result.source_url == "https://linkedin.com/jobs/view/123"

    def test_score_exactly_at_threshold_is_saved(self, tmp_path, monkeypatch):
        """Jobs with score exactly at MID_SCORE_THRESHOLD should be saved."""
        db_file = tmp_path / "test_thresh.db"
        from sqlmodel import create_engine, SQLModel
        test_engine = create_engine(f"sqlite:///{db_file}", echo=False)
        from backend.app.models import job, application, resume_version
        SQLModel.metadata.create_all(test_engine)
        monkeypatch.setattr("backend.app.database.engine", test_engine)
        monkeypatch.setattr("backend.app.config.MID_SCORE_THRESHOLD", 0.70)

        agent = _make_scout_with_mocked_calls(score=0.70)
        profile = make_profile()

        result = agent.run(
            raw_jd="Developer role",
            user_profile=profile,
            source="seek",
            auto_filter=True,
            notify=False,
        )
        # Exactly at threshold: 0.70 >= 0.70, should be saved
        assert result is not None
        assert result.match_score == 0.70

    def test_notify_false_does_not_send_notification(self, tmp_path, monkeypatch):
        """When notify=False, no notification should be sent even for high score jobs."""
        db_file = tmp_path / "test_notify.db"
        from sqlmodel import create_engine, SQLModel
        test_engine = create_engine(f"sqlite:///{db_file}", echo=False)
        from backend.app.models import job, application, resume_version
        SQLModel.metadata.create_all(test_engine)
        monkeypatch.setattr("backend.app.database.engine", test_engine)
        monkeypatch.setattr("backend.app.config.HIGH_SCORE_THRESHOLD", 0.80)
        monkeypatch.setattr("backend.app.config.MID_SCORE_THRESHOLD", 0.70)

        # Track notification calls
        notification_calls = []

        from backend.app import notifications as notif_module
        monkeypatch.setattr(notif_module, "push_high_score_job",
                            lambda job: notification_calls.append(job) or True)

        agent = _make_scout_with_mocked_calls(score=0.95)
        profile = make_profile()

        result = agent.run(
            raw_jd="High score job",
            user_profile=profile,
            source="seek",
            auto_filter=True,
            notify=False,  # Explicitly disabled
        )
        assert result is not None
        # No notification should be triggered
        assert len(notification_calls) == 0
