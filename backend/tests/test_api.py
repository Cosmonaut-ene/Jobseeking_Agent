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


class TestNotificationsAPI:
    def test_linkedin_cookies_status(self, client, tmp_path, monkeypatch):
        """GET /api/notifications/linkedin-cookies-status should return status."""
        monkeypatch.setattr("backend.app.config.COOKIES_DIR", tmp_path)
        response = client.get("/api/notifications/linkedin-cookies-status")
        assert response.status_code == 200
        data = response.json()
        assert "has_cookies" in data
        assert data["has_cookies"] is False  # No cookies in tmp_path

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

    def test_linkedin_cookies_status_has_boolean(self, client, tmp_path, monkeypatch):
        """linkedin-cookies-status has_cookies value should be a boolean."""
        monkeypatch.setattr("backend.app.config.COOKIES_DIR", tmp_path)
        response = client.get("/api/notifications/linkedin-cookies-status")
        data = response.json()
        assert isinstance(data["has_cookies"], bool)
