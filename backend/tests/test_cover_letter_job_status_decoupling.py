"""Regression test for a real UX-audit bug (see DECISIONS.md): generating a
cover letter used to flip Job.status straight to "applied" — before the
human had done anything on the actual job board. That made the status
badge shown across the UI lie, and made the separate human-confirmed
"Confirm applied" action pointless (Job.status already said "applied").

Job.status must only become "applied" via the confirmed Application
transition (see test_applications_router.py::test_confirming_applied_syncs_job_status).
Drafting a cover letter creates an Application in its default "ready"
state and must leave Job.status exactly as it was.
"""
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select


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

    profile_path = tmp_path / "user_profile.json"
    profile_path.write_text(json.dumps({
        "name": "Jane Doe", "target_roles": ["Software Engineer"],
        "skills": [], "experience": [], "projects": [], "education": [],
        "preferences": {"locations": []},
    }), encoding="utf-8")
    monkeypatch.setattr("backend.app.config.PROFILE_PATH", profile_path)

    from backend.app.main import app
    test_client = TestClient(app, raise_server_exceptions=False)
    test_client._test_engine = test_engine
    return test_client


def _seed_job_with_resume_version(engine, job_status="reviewed"):
    from backend.app.models.job import Job, JobStatus
    from backend.app.models.resume_version import ResumeVersion
    with Session(engine) as session:
        job = Job(source="manual", raw_jd="JD", title="Engineer", company="Acme",
                   status=JobStatus(job_status))
        session.add(job)
        session.commit()
        session.refresh(job)
        rv = ResumeVersion(job_id=job.id, content_json={"summary": "x"})
        session.add(rv)
        session.commit()
        return job.id


def test_generating_cover_letter_does_not_change_job_status(client):
    job_id = _seed_job_with_resume_version(client._test_engine, job_status="reviewed")

    with patch("backend.app.agents.cover_letter.CoverLetterAgent.generate", return_value=("Subject", "Body")), \
         patch("backend.app.agents.cover_letter.CoverLetterAgent.save", return_value="/fake/path.txt"):
        resp = client.post(f"/api/jobs/{job_id}/cover-letter")

    assert resp.status_code == 200
    from backend.app.models.job import Job
    with Session(client._test_engine) as session:
        job = session.get(Job, job_id)
    assert job.status.value == "reviewed"  # unchanged — must not silently become "applied"


def test_generating_cover_letter_creates_application_in_ready_state(client):
    job_id = _seed_job_with_resume_version(client._test_engine, job_status="new")

    with patch("backend.app.agents.cover_letter.CoverLetterAgent.generate", return_value=("Subject", "Body")), \
         patch("backend.app.agents.cover_letter.CoverLetterAgent.save", return_value="/fake/path.txt"):
        client.post(f"/api/jobs/{job_id}/cover-letter")

    from backend.app.models.application import Application
    with Session(client._test_engine) as session:
        application = session.exec(select(Application)).first()
    assert application is not None
    assert application.status.value == "ready"
