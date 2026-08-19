"""Tests for POST /api/ats/simulate (SPEC 附录 F.5 TASK-C03)."""
import json

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

    for router_module in ["backend.app.routers.ats", "backend.app.routers.jobs"]:
        import importlib
        m = importlib.import_module(router_module)
        if hasattr(m, "engine"):
            monkeypatch.setattr(m, "engine", test_engine)

    # Isolated profile + resumes dir per test
    profile_path = tmp_path / "user_profile.json"
    resumes_dir = tmp_path / "resumes"
    resumes_dir.mkdir()
    profile_path.write_text(json.dumps({
        "name": "Jane Doe",
        "target_roles": ["Software Engineer"],
        "skills": [{"name": "Kubernetes", "level": "intermediate", "years": 2.0}],
        "experience": [{"company": "Acme Corp", "role": "Engineer", "duration": "2022-2024", "bullets": []}],
        "projects": [],
        "education": [{"institution": "Test University", "degree": "BSc"}],
        "preferences": {"locations": []},
    }), encoding="utf-8")
    monkeypatch.setattr("backend.app.config.PROFILE_PATH", profile_path)
    monkeypatch.setattr("backend.app.routers.ats.RESUMES_DIR", resumes_dir)

    from backend.app.main import app
    return TestClient(app, raise_server_exceptions=False)


def _seed_job_and_resume_version(engine):
    from backend.app.models.job import Job
    from backend.app.models.resume_version import ResumeVersion

    with Session(engine) as session:
        job = Job(
            source="manual",
            raw_jd="Looking for a Kubernetes engineer",
            title="Engineer",
            company="Acme",
            match_score=0.9,
            gap_analysis={"resume_improvements": {"ats_keywords": ["Kubernetes"]}},
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        rv = ResumeVersion(
            job_id=job.id,
            content_json={"summary": "Kubernetes expert", "skills": ["Kubernetes"], "projects": [], "experience": []},
            ats_score=0.9,
        )
        session.add(rv)
        session.commit()
        session.refresh(rv)
        return job.id, rv.id


class TestSimulateEndpoint:
    def test_missing_resume_version_returns_404(self, client):
        resp = client.post("/api/ats/simulate", json={"resume_version_id": "nonexistent"})
        assert resp.status_code == 404

    def test_no_uploaded_resume_file_returns_400(self, client, monkeypatch, tmp_path):
        import backend.app.routers.ats as ats_module
        _, rv_id = _seed_job_and_resume_version(ats_module.engine)

        resp = client.post("/api/ats/simulate", json={"resume_version_id": rv_id})

        assert resp.status_code == 400
        assert "resume" in resp.json()["detail"].lower()

    def test_happy_path_returns_dual_scores(self, client, tmp_path):
        import backend.app.routers.ats as ats_module
        _, rv_id = _seed_job_and_resume_version(ats_module.engine)

        from docx import Document
        doc = Document()
        doc.add_paragraph("Jane Doe — Kubernetes — Acme Corp — Test University")
        doc.save(ats_module.RESUMES_DIR / "resume.docx")

        resp = client.post("/api/ats/simulate", json={"resume_version_id": rv_id})

        assert resp.status_code == 200
        body = resp.json()
        assert "deterministic_ats_score" in body
        assert "parseability" in body
        assert "keyword_match" in body
        assert isinstance(body["diagnosis"], list)

        # Persisted back onto the ResumeVersion row
        with Session(ats_module.engine) as session:
            from backend.app.models.resume_version import ResumeVersion
            rv = session.get(ResumeVersion, rv_id)
            assert rv.deterministic_ats_score == body["deterministic_ats_score"]
            assert rv.ats_report != {}
