"""Tests for the advisor report's response_rate fix (SPEC 附录 F.6 TASK-D01).

Application.status was a dead field (always "pending"), so response_rate
was mathematically guaranteed to be 0% forever. With the status machine
wired up, this verifies the denominator is "applications actually
submitted" (excludes `ready`), not every Application row ever created.
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    test_engine = create_engine(f"sqlite:///{db_file}", echo=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")
    monkeypatch.setattr("backend.app.database.engine", test_engine)

    from backend.app.models import application, job, resume_version  # noqa: F401
    SQLModel.metadata.create_all(test_engine)

    from backend.app.main import app
    test_client = TestClient(app, raise_server_exceptions=False)
    test_client._test_engine = test_engine
    return test_client


def _seed(engine, statuses: list[str]):
    from backend.app.models.application import Application, ApplicationStatus
    from backend.app.models.job import Job
    from backend.app.models.resume_version import ResumeVersion

    with Session(engine) as session:
        for status in statuses:
            job = Job(source="manual", raw_jd="JD")
            rv = ResumeVersion(job_id=job.id, content_json={})
            session.add(job)
            session.add(rv)
            session.commit()
            session.refresh(job)
            session.refresh(rv)
            session.add(Application(job_id=job.id, resume_version_id=rv.id, status=ApplicationStatus(status)))
        session.commit()


def test_response_rate_excludes_unsubmitted_ready_applications(client):
    # 3 ready (not actually applied yet) + 1 applied (no response yet) + 1 responded
    _seed(client._test_engine, ["ready", "ready", "ready", "applied", "responded"])

    resp = client.get("/api/dashboard/advisor")
    assert resp.status_code == 200
    stats = resp.json()["app_stats"]

    # denominator = submitted (applied + responded) = 2, not all 5 rows
    assert stats["applied"] == 2
    assert stats["responded"] == 1
    assert stats["response_rate"] == "50.0%"


def test_response_rate_is_zero_percent_string_not_error_when_no_submissions(client):
    _seed(client._test_engine, ["ready", "ready"])

    resp = client.get("/api/dashboard/advisor")
    stats = resp.json()["app_stats"]
    assert stats["applied"] == 0
    assert stats["response_rate"] == "0.0%"


def test_rejected_counts_as_a_response_not_silence(client):
    _seed(client._test_engine, ["applied", "rejected"])

    resp = client.get("/api/dashboard/advisor")
    stats = resp.json()["app_stats"]
    assert stats["applied"] == 2
    assert stats["response_rate"] == "50.0%"  # 1 of 2 submitted got a reply (the rejection)
