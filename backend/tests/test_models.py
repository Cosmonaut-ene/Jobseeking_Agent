"""Tests for data models."""
import pytest
from backend.app.models.job import Job, JobStatus
from backend.app.models.user_profile import (
    UserProfile, Skill, Experience, Project, Preferences, Education, Bullet
)
from backend.app.models.application import Application, ApplicationChannel
from backend.app.models.resume_version import ResumeVersion


class TestJobModel:
    def test_job_creation(self):
        job = Job(
            source="seek",
            raw_jd="Senior Python Developer needed",
            title="Senior Python Developer",
            company="Acme Corp",
            location="Sydney, NSW",
        )
        assert job.source == "seek"
        assert job.title == "Senior Python Developer"
        assert job.status == JobStatus.new
        assert job.match_score == 0.0
        assert job.notification_sent is False
        assert job.id is not None  # auto-generated UUID

    def test_job_status_enum(self):
        assert JobStatus.new == "new"
        assert JobStatus.applied == "applied"
        assert JobStatus.interview == "interview"
        assert JobStatus.offer == "offer"

    def test_job_defaults(self):
        job = Job(source="manual", raw_jd="test")
        assert job.skills_required == []
        assert job.gap_analysis == {}
        assert job.source_url == ""
        assert job.salary_range == ""

    def test_job_status_all_values(self):
        """All JobStatus values should be accessible."""
        assert JobStatus.reviewed == "reviewed"
        assert JobStatus.dismissed == "dismissed"
        assert JobStatus.rejected == "rejected"

    def test_job_created_at_not_none(self):
        job = Job(source="manual", raw_jd="test")
        assert job.created_at is not None
        assert job.updated_at is not None

    def test_job_id_is_unique(self):
        job1 = Job(source="manual", raw_jd="test1")
        job2 = Job(source="manual", raw_jd="test2")
        assert job1.id != job2.id


class TestUserProfile:
    def make_profile(self):
        return UserProfile(
            name="John Doe",
            target_roles=["Data Scientist", "ML Engineer"],
            skills=[
                Skill(name="Python", level="expert", years=5.0),
                Skill(name="TensorFlow", level="intermediate", years=2.0),
            ],
            experience=[
                Experience(
                    company="TechCorp",
                    role="Data Scientist",
                    duration="2022-01 ~ 2024-06",
                    bullets=[
                        Bullet(raw="Built ML models for recommendation system"),
                    ],
                )
            ],
            projects=[
                Project(
                    name="Fraud Detection",
                    description="ML-based fraud detection system",
                    tech_stack=["Python", "scikit-learn", "FastAPI"],
                )
            ],
            preferences=Preferences(
                locations=["Sydney, NSW"],
                job_types=["full-time"],
            ),
            education=[
                Education(
                    institution="University of Sydney",
                    degree="Bachelor",
                    field="Computer Science",
                    duration="2018-02 ~ 2022-06",
                )
            ],
        )

    def test_profile_creation(self):
        profile = self.make_profile()
        assert profile.name == "John Doe"
        assert len(profile.target_roles) == 2
        assert len(profile.skills) == 2
        assert profile.skills[0].name == "Python"
        assert profile.skills[0].level == "expert"
        assert profile.skills[0].years == 5.0

    def test_to_prompt_text(self):
        profile = self.make_profile()
        text = profile.to_prompt_text()
        assert "John Doe" in text
        assert "Data Scientist" in text
        assert "Python" in text
        assert "TechCorp" in text
        assert "Fraud Detection" in text
        assert "University of Sydney" in text

    def test_to_prompt_text_contains_skills_section(self):
        profile = self.make_profile()
        text = profile.to_prompt_text()
        assert "## Skills" in text
        assert "## Experience" in text
        assert "## Projects" in text
        assert "## Education" in text

    def test_to_prompt_text_includes_preferred_locations(self):
        profile = self.make_profile()
        text = profile.to_prompt_text()
        assert "Sydney" in text

    def test_skill_defaults(self):
        skill = Skill(name="SQL", level="beginner")
        assert skill.years == 0.0

    def test_bullet_defaults(self):
        bullet = Bullet(raw="Did something important")
        assert bullet.tech == []
        assert bullet.metric == ""

    def test_education_defaults(self):
        edu = Education(institution="USYD", degree="Master", field="CS")
        assert edu.duration == ""
        assert edu.gpa == ""

    def test_preferences_defaults(self):
        prefs = Preferences()
        assert prefs.locations == []
        assert prefs.job_types == []
        assert prefs.salary_range is None

    def test_project_defaults(self):
        proj = Project(name="My Project", description="A test project")
        assert proj.tech_stack == []
        assert proj.bullets == []

    def test_profile_with_no_education(self):
        profile = UserProfile(
            name="Jane",
            target_roles=["Engineer"],
            skills=[],
            experience=[],
            projects=[],
            preferences=Preferences(),
        )
        text = profile.to_prompt_text()
        # Education section should not appear if empty
        assert "## Education" not in text


class TestApplicationModel:
    def test_application_defaults(self):
        app = Application(
            job_id="test-job-id",
            resume_version_id="test-rv-id",
        )
        assert app.channel == ApplicationChannel.easy_apply
        assert app.status == "pending"
        assert app.notes == ""

    def test_application_channel_enum(self):
        assert ApplicationChannel.email == "email"
        assert ApplicationChannel.easy_apply == "easy_apply"
        assert ApplicationChannel.manual == "manual"

    def test_application_id_auto_generated(self):
        app = Application(
            job_id="test-job-id",
            resume_version_id="test-rv-id",
        )
        assert app.id is not None
        assert len(app.id) > 0

    def test_application_applied_at_not_none(self):
        app = Application(
            job_id="test-job-id",
            resume_version_id="test-rv-id",
        )
        assert app.applied_at is not None

    def test_application_follow_up_date_defaults_none(self):
        app = Application(
            job_id="test-job-id",
            resume_version_id="test-rv-id",
        )
        assert app.follow_up_date is None


class TestResumeVersion:
    def test_resume_version_defaults(self):
        rv = ResumeVersion(job_id="test-job-id")
        assert rv.ats_score == 0.0
        assert rv.changes_summary == ""
        assert rv.content_json == {}

    def test_resume_version_id_auto_generated(self):
        rv = ResumeVersion(job_id="test-job-id")
        assert rv.id is not None
        assert len(rv.id) > 0

    def test_resume_version_created_at_not_none(self):
        rv = ResumeVersion(job_id="test-job-id")
        assert rv.created_at is not None

    def test_resume_version_with_content(self):
        rv = ResumeVersion(
            job_id="test-job-id",
            content_json={"summary": "Experienced developer", "skills": ["Python"]},
            ats_score=0.85,
            changes_summary="Added Python keyword",
        )
        assert rv.ats_score == 0.85
        assert rv.changes_summary == "Added Python keyword"
        assert rv.content_json["summary"] == "Experienced developer"
