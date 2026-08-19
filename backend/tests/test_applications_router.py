"""Tests for the applications router (SPEC 附录 F.6 TASK-D01/D02)."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    test_engine = create_engine(f"sqlite:///{db_file}", echo=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    monkeypatch.setattr("backend.app.database.engine", test_engine)

    from backend.app.models import application, job, resume_version  # noqa: F401
    SQLModel.metadata.create_all(test_engine)

    for router_module in ["backend.app.routers.applications"]:
        import importlib
        m = importlib.import_module(router_module)
        monkeypatch.setattr(m, "engine", test_engine)

    from backend.app.main import app
    test_client = TestClient(app, raise_server_exceptions=False)
    test_client._test_engine = test_engine  # stash for helpers below
    return test_client


def _seed_application(engine, status="ready"):
    from backend.app.models.application import Application, ApplicationStatus
    from backend.app.models.job import Job
    from backend.app.models.resume_version import ResumeVersion

    with Session(engine) as session:
        job = Job(source="manual", raw_jd="JD", title="Engineer", company="Acme", match_score=0.9)
        rv = ResumeVersion(job_id=job.id, content_json={})
        session.add(job)
        session.add(rv)
        session.commit()
        session.refresh(job)
        session.refresh(rv)

        application = Application(
            job_id=job.id, resume_version_id=rv.id, status=ApplicationStatus(status)
        )
        session.add(application)
        session.commit()
        session.refresh(application)
        return application.id


class TestStatusTransitions:
    def test_valid_transition_ready_to_applied(self, client):
        app_id = _seed_application(client._test_engine, status="ready")
        resp = client.put(f"/api/applications/{app_id}/status", json={"status": "applied"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "applied"

    @pytest.mark.parametrize("next_status", ["responded", "interview", "rejected"])
    def test_valid_transitions_from_applied(self, client, next_status):
        app_id = _seed_application(client._test_engine, status="applied")
        resp = client.put(f"/api/applications/{app_id}/status", json={"status": next_status})
        assert resp.status_code == 200
        assert resp.json()["status"] == next_status

    def test_invalid_transition_skips_applied(self, client):
        """ready -> interview directly is not allowed; must go through applied."""
        app_id = _seed_application(client._test_engine, status="ready")
        resp = client.put(f"/api/applications/{app_id}/status", json={"status": "interview"})
        assert resp.status_code == 400

    def test_invalid_transition_from_terminal_state(self, client):
        app_id = _seed_application(client._test_engine, status="rejected")
        resp = client.put(f"/api/applications/{app_id}/status", json={"status": "applied"})
        assert resp.status_code == 400

    def test_same_status_transition_is_a_noop_not_an_error(self, client):
        app_id = _seed_application(client._test_engine, status="applied")
        resp = client.put(f"/api/applications/{app_id}/status", json={"status": "applied"})
        assert resp.status_code == 200

    def test_update_nonexistent_application_returns_404(self, client):
        resp = client.put("/api/applications/does-not-exist/status", json={"status": "applied"})
        assert resp.status_code == 404


class TestPushReminder:
    def test_no_ready_applications_returns_sent_false(self, client):
        resp = client.post("/api/applications/push-reminder")
        assert resp.status_code == 200
        body = resp.json()
        assert body["sent"] is False
        assert body["count"] == 0

    def test_with_ready_applications_calls_notifications(self, client, monkeypatch):
        _seed_application(client._test_engine, status="ready")
        called = {}

        def _fake_push(applications, jobs_by_id):
            called["count"] = len(applications)
            return True

        monkeypatch.setattr(
            "backend.app.routers.applications.notifications.push_ready_applications_reminder",
            _fake_push,
        )

        resp = client.post("/api/applications/push-reminder")
        assert resp.status_code == 200
        body = resp.json()
        assert body["sent"] is True
        assert body["count"] == 1
        assert called["count"] == 1

    def test_webhook_unconfigured_degrades_without_error(self, client, monkeypatch):
        """_send() itself returns False when no webhook URL — push_reminder should
        surface sent=False, not raise or 500."""
        _seed_application(client._test_engine, status="ready")
        monkeypatch.setattr("backend.app.notifications.NOTIFICATION_WEBHOOK_URL", "")

        resp = client.post("/api/applications/push-reminder")
        assert resp.status_code == 200
        assert resp.json()["sent"] is False
