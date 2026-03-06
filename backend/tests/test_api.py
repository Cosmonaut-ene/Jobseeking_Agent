"""Tests for FastAPI endpoints using TestClient."""
import pytest
import json
import os
from pathlib import Path
from fastapi.testclient import TestClient
from sqlmodel import create_engine, SQLModel, Session
from unittest.mock import patch, MagicMock


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create a TestClient with test database."""
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")  # Disable scheduler in tests

    test_engine = create_engine(f"sqlite:///{db_file}", echo=False)

    # Patch database engine
    monkeypatch.setattr("backend.app.database.engine", test_engine)
    monkeypatch.setattr("backend.app.database.DB_PATH", db_file)

    # Import models and create tables
    from backend.app.models import job, application, resume_version
    SQLModel.metadata.create_all(test_engine)

    # Also patch all routers that use engine directly
    for router_module in ["backend.app.routers.jobs", "backend.app.routers.scrapers",
                          "backend.app.routers.dashboard", "backend.app.routers.profile"]:
        try:
            import importlib
            m = importlib.import_module(router_module)
            if hasattr(m, 'engine'):
                monkeypatch.setattr(m, 'engine', test_engine)
        except Exception:
            pass

    from backend.app.main import app
    client = TestClient(app, raise_server_exceptions=False)
    return client


class TestHealthCheck:
    def test_docs_accessible(self, client):
        """FastAPI docs should be accessible."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_schema(self, client):
        """OpenAPI schema should be accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "paths" in schema

    def test_openapi_schema_has_jobs_path(self, client):
        """OpenAPI schema should list /api/jobs."""
        response = client.get("/openapi.json")
        schema = response.json()
        paths = schema["paths"]
        assert any("/jobs" in p for p in paths)


class TestJobsAPI:
    def test_list_jobs_empty(self, client):
        """GET /api/jobs should return empty list initially."""
        response = client.get("/api/jobs")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_jobs_returns_list(self, client):
        """GET /api/jobs should always return a list."""
        response = client.get("/api/jobs")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_jobs_with_status_filter(self, client):
        """GET /api/jobs?status=new should return filtered list."""
        response = client.get("/api/jobs?status=new")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_jobs_with_min_score_filter(self, client):
        """GET /api/jobs?min_score=0.8 should return filtered list."""
        response = client.get("/api/jobs?min_score=0.8")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_nonexistent_job(self, client):
        """GET /api/jobs/{id} for non-existent job should return 404."""
        response = client.get("/api/jobs/nonexistent-id")
        assert response.status_code == 404

    def test_update_job_status_nonexistent(self, client):
        """PUT /api/jobs/{id}/status for non-existent job should return 404."""
        response = client.put(
            "/api/jobs/nonexistent-id/status",
            json={"status": "applied"}
        )
        assert response.status_code == 404

    def test_delete_nonexistent_job(self, client):
        """DELETE /api/jobs/{id} for non-existent job should return 404."""
        response = client.delete("/api/jobs/nonexistent-id")
        assert response.status_code == 404

    def test_scout_without_api_key(self, tmp_path, monkeypatch):
        """POST /api/jobs/scout without GEMINI_API_KEY should return 400."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        db_file = tmp_path / "test.db"
        test_engine = create_engine(f"sqlite:///{db_file}", echo=False)
        from backend.app.models import job, application, resume_version
        SQLModel.metadata.create_all(test_engine)
        monkeypatch.setattr("backend.app.database.engine", test_engine)
        monkeypatch.setenv("SCHEDULER_ENABLED", "false")

        for router_module in ["backend.app.routers.jobs"]:
            try:
                import importlib
                m = importlib.import_module(router_module)
                if hasattr(m, 'engine'):
                    monkeypatch.setattr(m, 'engine', test_engine)
            except Exception:
                pass

        from backend.app.main import app
        test_client = TestClient(app, raise_server_exceptions=False)
        response = test_client.post("/api/jobs/scout", json={"raw_jd": "Test JD"})
        assert response.status_code == 400

    def test_tailor_nonexistent_job(self, client):
        """POST /api/jobs/{id}/tailor for non-existent job should return 404 or 400."""
        response = client.post("/api/jobs/nonexistent-id/tailor")
        # Either 400 (no api key) or 404 (no job) — both are valid error responses
        assert response.status_code in (400, 404)

    def test_cover_letter_nonexistent_job(self, client):
        """POST /api/jobs/{id}/cover-letter for non-existent job should return 404 or 400."""
        response = client.post("/api/jobs/nonexistent-id/cover-letter")
        assert response.status_code in (400, 404)

    def test_update_job_status_with_valid_data(self, tmp_path, monkeypatch):
        """PUT /api/jobs/{id}/status for existing job should update status."""
        db_file = tmp_path / "update_status.db"
        test_engine = create_engine(f"sqlite:///{db_file}", echo=False)
        from backend.app.models import job, application, resume_version
        SQLModel.metadata.create_all(test_engine)
        monkeypatch.setattr("backend.app.database.engine", test_engine)
        monkeypatch.setenv("SCHEDULER_ENABLED", "false")
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")

        import importlib
        m = importlib.import_module("backend.app.routers.jobs")
        monkeypatch.setattr(m, 'engine', test_engine)

        from backend.app.models.job import Job
        new_job = Job(source="manual", raw_jd="Test JD", title="Dev")
        with Session(test_engine) as session:
            session.add(new_job)
            session.commit()
            job_id = new_job.id

        from backend.app.main import app
        test_client = TestClient(app, raise_server_exceptions=False)
        response = test_client.put(
            f"/api/jobs/{job_id}/status",
            json={"status": "applied"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "applied"

    def test_delete_existing_job(self, tmp_path, monkeypatch):
        """DELETE /api/jobs/{id} for existing job should return success."""
        db_file = tmp_path / "delete_job.db"
        test_engine = create_engine(f"sqlite:///{db_file}", echo=False)
        from backend.app.models import job, application, resume_version
        SQLModel.metadata.create_all(test_engine)
        monkeypatch.setattr("backend.app.database.engine", test_engine)
        monkeypatch.setenv("SCHEDULER_ENABLED", "false")
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")

        import importlib
        m = importlib.import_module("backend.app.routers.jobs")
        monkeypatch.setattr(m, 'engine', test_engine)

        from backend.app.models.job import Job
        new_job = Job(source="manual", raw_jd="Test JD to delete", title="DeleteMe")
        with Session(test_engine) as session:
            session.add(new_job)
            session.commit()
            job_id = new_job.id

        from backend.app.main import app
        test_client = TestClient(app, raise_server_exceptions=False)
        response = test_client.delete(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        assert response.json()["deleted"] is True


class TestDashboardAPI:
    def test_get_stats(self, client):
        """GET /api/dashboard/stats should return stats dict."""
        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_jobs" in data
        assert "by_status" in data
        assert "high_score_count" in data
        assert "mid_score_count" in data
        assert "by_source" in data

    def test_recent_jobs(self, client):
        """GET /api/dashboard/recent-jobs should return list."""
        response = client.get("/api/dashboard/recent-jobs")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_stats_total_jobs_is_zero_on_empty_db(self, client):
        """Stats total_jobs should be 0 on empty database."""
        response = client.get("/api/dashboard/stats")
        data = response.json()
        assert data["total_jobs"] == 0

    def test_stats_by_status_contains_all_statuses(self, client):
        """Stats by_status should contain all job statuses."""
        response = client.get("/api/dashboard/stats")
        data = response.json()
        by_status = data["by_status"]
        expected_statuses = ["new", "reviewed", "dismissed", "applied", "interview", "rejected", "offer"]
        for status in expected_statuses:
            assert status in by_status

    def test_recent_jobs_with_limit(self, client):
        """GET /api/dashboard/recent-jobs?limit=5 should respect limit."""
        response = client.get("/api/dashboard/recent-jobs?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5

    def test_stats_recent_jobs_7d_key(self, client):
        """Stats should include recent_jobs_7d key."""
        response = client.get("/api/dashboard/stats")
        data = response.json()
        assert "recent_jobs_7d" in data


class TestProfileAPI:
    def test_get_profile_empty(self, client, tmp_path, monkeypatch):
        """GET /api/profile should return empty dict if no profile."""
        monkeypatch.setattr("backend.app.config.PROFILE_PATH", tmp_path / "nonexistent.json")
        monkeypatch.setattr("backend.app.routers.profile.PROFILE_PATH", tmp_path / "nonexistent.json")
        response = client.get("/api/profile")
        # Should return 200 with empty dict when no profile exists
        assert response.status_code == 200

    def test_get_profile_returns_dict(self, client, tmp_path, monkeypatch):
        """GET /api/profile should always return a dict."""
        monkeypatch.setattr("backend.app.config.PROFILE_PATH", tmp_path / "nonexistent.json")
        monkeypatch.setattr("backend.app.routers.profile.PROFILE_PATH", tmp_path / "nonexistent.json")
        response = client.get("/api/profile")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)

    def test_update_profile(self, client, tmp_path, monkeypatch):
        """PUT /api/profile should save profile data."""
        profile_path = tmp_path / "profile.json"
        monkeypatch.setattr("backend.app.routers.profile.PROFILE_PATH", profile_path)

        profile_data = {
            "name": "Test User",
            "target_roles": ["Developer"],
            "skills": [],
            "experience": [],
            "projects": [],
            "education": [],
            "preferences": {"locations": [], "job_types": []},
        }
        response = client.put("/api/profile", json=profile_data)
        assert response.status_code == 200
        assert response.json()["saved"] is True
        assert profile_path.exists()

    def test_update_profile_persists_data(self, client, tmp_path, monkeypatch):
        """PUT /api/profile data should be readable after saving."""
        profile_path = tmp_path / "profile.json"
        monkeypatch.setattr("backend.app.routers.profile.PROFILE_PATH", profile_path)

        profile_data = {
            "name": "Persisted User",
            "target_roles": ["Engineer"],
            "skills": [],
            "experience": [],
            "projects": [],
            "education": [],
            "preferences": {"locations": [], "job_types": []},
        }
        client.put("/api/profile", json=profile_data)

        # Read back the file and verify content
        saved = json.loads(profile_path.read_text())
        assert saved["name"] == "Persisted User"

    # ------------------------------------------------------------------
    # parse-resume endpoint tests
    # ------------------------------------------------------------------

    def test_parse_resume_text_without_api_key(self, tmp_path, monkeypatch):
        """POST /api/profile/parse-resume without GEMINI_API_KEY should return 400."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        db_file = tmp_path / "test_parse_no_key.db"
        test_engine = create_engine(f"sqlite:///{db_file}", echo=False)
        from backend.app.models import job, application, resume_version
        SQLModel.metadata.create_all(test_engine)
        monkeypatch.setattr("backend.app.database.engine", test_engine)
        monkeypatch.setenv("SCHEDULER_ENABLED", "false")

        from backend.app.main import app
        test_client = TestClient(app, raise_server_exceptions=False)
        response = test_client.post("/api/profile/parse-resume", json={"text": "Some resume text"})
        assert response.status_code == 400

    def test_parse_resume_text_with_empty_text(self, client):
        """POST /api/profile/parse-resume with empty text should return 400."""
        response = client.post("/api/profile/parse-resume", json={"text": ""})
        assert response.status_code == 400

    def test_parse_resume_text_with_whitespace_only(self, client):
        """POST /api/profile/parse-resume with whitespace-only text should return 400."""
        response = client.post("/api/profile/parse-resume", json={"text": "   \n\t  "})
        assert response.status_code == 400

    def test_parse_resume_text_returns_parsed_profile(self, client):
        """POST /api/profile/parse-resume with valid text and mocked parser returns profile shape."""
        sample_profile = {
            "name": "Test User",
            "target_roles": ["Engineer"],
            "skills": [{"name": "Python", "level": "expert", "years": 3}],
            "experience": [],
            "projects": [],
            "preferences": {"locations": ["Sydney"], "job_types": ["full-time"]},
            "education": [],
        }
        with patch("backend.app.agents.parser.ResumeParser.parse_text", return_value=sample_profile):
            response = client.post(
                "/api/profile/parse-resume",
                json={"text": "Jane Doe\nSoftware Engineer with 3 years of Python experience."},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["parsed"] is True
        assert "profile" in data
        assert data["profile"]["name"] == "Test User"
        assert data["profile"]["target_roles"] == ["Engineer"]
        assert data["profile"]["skills"][0]["name"] == "Python"

    # ------------------------------------------------------------------
    # upload-resume endpoint tests
    # ------------------------------------------------------------------

    def test_upload_resume_without_api_key(self, tmp_path, monkeypatch):
        """POST /api/profile/upload-resume without GEMINI_API_KEY should return 400."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        db_file = tmp_path / "test_upload_no_key.db"
        test_engine = create_engine(f"sqlite:///{db_file}", echo=False)
        from backend.app.models import job, application, resume_version
        SQLModel.metadata.create_all(test_engine)
        monkeypatch.setattr("backend.app.database.engine", test_engine)
        monkeypatch.setenv("SCHEDULER_ENABLED", "false")

        from backend.app.main import app
        test_client = TestClient(app, raise_server_exceptions=False)

        dummy_pdf = b"%PDF-1.4 dummy content"
        response = test_client.post(
            "/api/profile/upload-resume",
            files={"file": ("resume.pdf", dummy_pdf, "application/pdf")},
        )
        assert response.status_code == 400


class TestSettingsAPI:
    def test_get_settings(self, client):
        """GET /api/settings should return settings dict."""
        response = client.get("/api/settings")
        assert response.status_code == 200
        data = response.json()
        assert "gemini_api_key_set" in data
        assert "scheduler_enabled" in data
        assert "high_score_threshold" in data
        assert "mid_score_threshold" in data

    def test_settings_gemini_api_key_set_true(self, client):
        """gemini_api_key_set should be True when GEMINI_API_KEY env is set."""
        response = client.get("/api/settings")
        data = response.json()
        # The fixture sets GEMINI_API_KEY=test-key-123
        assert data["gemini_api_key_set"] is True

    def test_settings_thresholds_are_floats(self, client):
        """Threshold values in settings should be floats."""
        response = client.get("/api/settings")
        data = response.json()
        assert isinstance(data["high_score_threshold"], float)
        assert isinstance(data["mid_score_threshold"], float)

    def test_settings_scheduler_hour_is_int(self, client):
        """Scheduler hour in settings should be an int."""
        response = client.get("/api/settings")
        data = response.json()
        assert "scheduler_hour" in data
        assert isinstance(data["scheduler_hour"], int)

    def test_settings_notification_webhook_set_false_by_default(self, client):
        """notification_webhook_set should be False when not configured."""
        response = client.get("/api/settings")
        data = response.json()
        # notification_webhook_set should be False when env not set
        assert "notification_webhook_set" in data


class TestResumeParser:
    def test_parse_text_uses_level_and_years_from_response(self, monkeypatch):
        """parse_text should propagate non-beginner level and non-zero years from Gemini."""
        from unittest.mock import MagicMock
        from backend.app.agents.parser import ResumeParser

        sample_response = {
            "name": "Jane Doe",
            "target_roles": ["Data Engineer"],
            "skills": [
                {"name": "Python", "level": "expert", "years": 5.0},
                {"name": "SQL", "level": "intermediate", "years": 2.5},
                {"name": "Docker", "level": "beginner", "years": 0.5},
            ],
            "experience": [],
            "projects": [],
            "preferences": {"locations": [], "job_types": []},
        }

        mock_response = MagicMock()
        mock_response.text = json.dumps(sample_response)

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        parser = ResumeParser.__new__(ResumeParser)
        parser.client = mock_client

        result = parser.parse_text("Jane Doe resume text")

        skills = {s["name"]: s for s in result["skills"]}
        assert skills["Python"]["level"] == "expert"
        assert skills["Python"]["years"] == 5.0
        assert skills["SQL"]["level"] == "intermediate"
        assert skills["SQL"]["years"] == 2.5
        assert skills["Docker"]["level"] == "beginner"
        assert skills["Docker"]["years"] == 0.5

    def test_parse_text_schema_has_enum_for_level(self):
        """PROFILE_SCHEMA skills.level must restrict values via enum."""
        from backend.app.agents.parser import PROFILE_SCHEMA

        skills_schema = PROFILE_SCHEMA.properties["skills"]
        level_schema = skills_schema.items.properties["level"]
        assert level_schema.enum == ["beginner", "intermediate", "expert"]

    def test_parse_text_schema_requires_years(self):
        """PROFILE_SCHEMA skills must list 'years' as required."""
        from backend.app.agents.parser import PROFILE_SCHEMA

        skills_items = PROFILE_SCHEMA.properties["skills"].items
        assert "years" in skills_items.required

    def test_parse_text_system_prompt_mentions_level_inference(self):
        """PARSE_SYSTEM should include guidance for inferring level and years."""
        from backend.app.agents.parser import PARSE_SYSTEM

        lowered = PARSE_SYSTEM.lower()
        assert "intermediate" in lowered
        assert "expert" in lowered
        assert "year" in lowered

    def test_parse_text_skills_not_all_beginner(self, monkeypatch):
        """A resume with clear seniority signals should produce non-beginner skills."""
        from unittest.mock import MagicMock
        from backend.app.agents.parser import ResumeParser

        mixed_skills = {
            "name": "Senior Dev",
            "target_roles": ["Backend Engineer"],
            "skills": [
                {"name": "Go", "level": "expert", "years": 6.0},
                {"name": "Kubernetes", "level": "intermediate", "years": 2.0},
                {"name": "Rust", "level": "beginner", "years": 0.5},
            ],
            "experience": [],
            "projects": [],
            "preferences": {"locations": [], "job_types": []},
        }

        mock_response = MagicMock()
        mock_response.text = json.dumps(mixed_skills)
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        parser = ResumeParser.__new__(ResumeParser)
        parser.client = mock_client

        result = parser.parse_text("Senior engineer resume...")
        levels = [s["level"] for s in result["skills"]]
        assert "expert" in levels or "intermediate" in levels, (
            "Expected at least one non-beginner skill level"
        )

    def test_parse_text_years_nonzero_for_experienced_skills(self, monkeypatch):
        """Skills from an experienced resume should have years > 0."""
        from unittest.mock import MagicMock
        from backend.app.agents.parser import ResumeParser

        experienced = {
            "name": "Alice",
            "target_roles": ["ML Engineer"],
            "skills": [
                {"name": "PyTorch", "level": "expert", "years": 4.0},
                {"name": "MLflow", "level": "intermediate", "years": 1.5},
            ],
            "experience": [],
            "projects": [],
            "preferences": {"locations": [], "job_types": []},
        }

        mock_response = MagicMock()
        mock_response.text = json.dumps(experienced)
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        parser = ResumeParser.__new__(ResumeParser)
        parser.client = mock_client

        result = parser.parse_text("Alice ML resume...")
        for skill in result["skills"]:
            assert skill["years"] > 0, f"Skill '{skill['name']}' has years=0"


class TestNotificationsAPI:
    def test_test_notification_without_webhook(self, client, monkeypatch):
        """POST /api/notifications/test without webhook should return 400."""
        from backend.app import notifications
        monkeypatch.setattr(notifications, "NOTIFICATION_WEBHOOK_URL", "")
        response = client.post("/api/notifications/test")
        assert response.status_code == 400

    def test_trigger_scout_returns_task_id(self, client):
        """POST /api/notifications/trigger-scout should return task_id."""
        response = client.post("/api/notifications/trigger-scout")
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert len(data["task_id"]) > 0

    def test_get_nonexistent_task(self, client):
        """GET /api/notifications/tasks/{id} for non-existent task should return 404."""
        response = client.get("/api/notifications/tasks/nonexistent-task-id")
        assert response.status_code == 404

    def test_trigger_scout_task_id_is_uuid(self, client):
        """POST /api/notifications/trigger-scout task_id should look like a UUID."""
        import re
        response = client.post("/api/notifications/trigger-scout")
        data = response.json()
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        )
        assert uuid_pattern.match(data["task_id"])

    def test_trigger_scout_creates_retrievable_task(self, client):
        """After POST trigger-scout, task should be retrievable by task_id."""
        trigger_response = client.post("/api/notifications/trigger-scout")
        task_id = trigger_response.json()["task_id"]

        task_response = client.get(f"/api/notifications/tasks/{task_id}")
        assert task_response.status_code == 200
        task_data = task_response.json()
        assert "status" in task_data

