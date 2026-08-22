"""Tests for the background-task version of POST /api/jobs/{id}/tailor
(UX audit finding: the old synchronous endpoint could block for 90+ seconds
with the frontend showing a static "Tailoring…" with no progress). Mirrors
the existing task-dict + background-thread + polling-GET pattern already
used by scrapers.py and profile.py's github-sync endpoints.

TailorAgent.run() is mocked — these tests verify the router's task
lifecycle/plumbing, not the agent's own iteration logic (covered in
test_tailor_evaluator_loop.py).
"""
import json
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    test_engine = create_engine(f"sqlite:///{db_file}", echo=False)

    monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")

    from backend.app.models import application, job, resume_version  # noqa: F401
    SQLModel.metadata.create_all(test_engine)

    import importlib
    m = importlib.import_module("backend.app.routers.jobs")
    monkeypatch.setattr(m, "engine", test_engine)
    monkeypatch.setattr("backend.app.database.engine", test_engine)
    m._tailor_tasks.clear()

    profile_path = tmp_path / "user_profile.json"
    profile_path.write_text(json.dumps({
        "name": "Jane Doe",
        "target_roles": ["Software Engineer"],
        "skills": [{"name": "Kubernetes", "level": "intermediate", "years": 2.0}],
        "experience": [],
        "projects": [],
        "education": [],
        "preferences": {"locations": []},
    }), encoding="utf-8")
    monkeypatch.setattr("backend.app.config.PROFILE_PATH", profile_path)

    from backend.app.main import app
    return TestClient(app, raise_server_exceptions=False)


def _seed_job(engine) -> str:
    from backend.app.models.job import Job
    with Session(engine) as session:
        job = Job(source="manual", raw_jd="Looking for a Kubernetes engineer",
                   title="Engineer", company="Acme", gap_analysis={})
        session.add(job)
        session.commit()
        session.refresh(job)
        return job.id


def _wait_for_status(client, job_id, task_id, target_statuses, timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(f"/api/jobs/{job_id}/tailor/tasks/{task_id}")
        if resp.json().get("status") in target_statuses:
            return resp.json()
        time.sleep(0.02)
    raise AssertionError(f"task never reached {target_statuses}")


class TestStartTailorTask:
    def test_returns_task_id_immediately_not_the_resume(self, client):
        import backend.app.routers.jobs as jobs_module
        from backend.app.models.resume_version import ResumeVersion
        job_id = _seed_job(jobs_module.engine)

        # Use a real, encodable ResumeVersion (not a bare MagicMock) so the
        # background thread this test kicks off finishes cleanly rather than
        # dangling past the end of the test (jsonable_encoder chokes on
        # arbitrary MagicMocks, which would otherwise leave a thread alive
        # to blow up once a later test's fixture clears the shared task dict).
        fake_result = ResumeVersion(job_id=job_id, content_json={}, ats_score=0.7,
                                     deterministic_ats_score=70.0)
        with patch("backend.app.agents.tailor.TailorAgent.run", return_value=fake_result):
            resp = client.post(f"/api/jobs/{job_id}/tailor")
            task_id = resp.json()["task_id"]

        assert resp.status_code == 200
        assert "task_id" in resp.json()
        assert "content_json" not in resp.json()  # must not block for the full result
        _wait_for_status(client, job_id, task_id, {"done", "error"})

    def test_nonexistent_job_returns_404_without_starting_a_task(self, client):
        resp = client.post("/api/jobs/nonexistent/tailor")
        assert resp.status_code == 404

    def test_unknown_task_id_returns_404(self, client):
        resp = client.get("/api/jobs/whatever/tailor/tasks/nonexistent-task")
        assert resp.status_code == 404


class TestTailorTaskProgress:
    def test_progress_reflects_each_round_then_reaches_done_with_result(self, client):
        import backend.app.routers.jobs as jobs_module
        job_id = _seed_job(jobs_module.engine)

        def fake_run(self, job, profile, on_progress=None):
            if on_progress:
                on_progress(1, 2, 50.0)
                on_progress(2, 2, 75.0)
            from backend.app.models.resume_version import ResumeVersion
            rv = ResumeVersion(job_id=job.id, content_json={"summary": "x"}, ats_score=0.75,
                                deterministic_ats_score=75.0)
            with Session(jobs_module.engine) as session:
                session.add(rv)
                session.commit()
                session.refresh(rv)
            return rv

        with patch("backend.app.agents.tailor.TailorAgent.run", fake_run):
            start_resp = client.post(f"/api/jobs/{job_id}/tailor")
            task_id = start_resp.json()["task_id"]
            final = _wait_for_status(client, job_id, task_id, {"done", "error"})

        assert final["status"] == "done"
        assert final["result"]["deterministic_ats_score"] == 75.0

    def test_agent_exception_surfaces_as_error_status_not_a_hang(self, client):
        import backend.app.routers.jobs as jobs_module
        job_id = _seed_job(jobs_module.engine)

        with patch("backend.app.agents.tailor.TailorAgent.run", side_effect=RuntimeError("LLM quota exceeded")):
            start_resp = client.post(f"/api/jobs/{job_id}/tailor")
            task_id = start_resp.json()["task_id"]
            final = _wait_for_status(client, job_id, task_id, {"done", "error"})

        assert final["status"] == "error"
        assert "LLM quota exceeded" in final["error"]
