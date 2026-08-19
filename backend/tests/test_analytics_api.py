"""Tests for the Analytics router (TASK-D02) — raw SQL over analytics_demo.db."""
import sqlite3

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine


def _seed_analytics_db(db_path) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE demo_company (id INTEGER PRIMARY KEY, name TEXT, industry TEXT);
        CREATE TABLE demo_job (
            id TEXT PRIMARY KEY, source TEXT, title TEXT, company_id INTEGER,
            location TEXT, salary_min INTEGER, salary_max INTEGER,
            match_score REAL, gap_analysis_json TEXT, status TEXT, created_at TEXT
        );
        CREATE TABLE demo_application (id TEXT PRIMARY KEY, job_id TEXT, channel TEXT, applied_at TEXT);
        CREATE TABLE demo_application_status_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, application_id TEXT, status TEXT, changed_at TEXT
        );
        """
    )
    conn.execute("INSERT INTO demo_company VALUES (1, 'Acme Corp', 'Technology')")
    conn.execute(
        "INSERT INTO demo_job VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "job-1", "seek", "Data Engineer", 1, "Sydney NSW", 100000, 120000, 0.75,
            '{"ats_pct": 75, "strong_matches": ["SQL"], "missing_skills": ["Airflow"], '
            '"unmet_requirements": [], "notes": ""}',
            "applied", "2026-01-01T00:00:00+00:00",
        ),
    )
    conn.execute(
        "INSERT INTO demo_application VALUES ('app-1', 'job-1', 'email', '2026-01-02T00:00:00+00:00')"
    )
    conn.execute(
        "INSERT INTO demo_application_status_log (application_id, status, changed_at) VALUES (?, ?, ?)",
        ("app-1", "submitted", "2026-01-02T00:00:00+00:00"),
    )
    conn.commit()
    conn.close()


def _patch_production_db(tmp_path, monkeypatch) -> None:
    """Isolate the production engine too — TestClient triggers app startup (init_db())."""
    prod_engine = create_engine(f"sqlite:///{tmp_path / 'prod.db'}", echo=False)
    monkeypatch.setattr("backend.app.database.engine", prod_engine)
    monkeypatch.setattr("backend.app.database.DB_PATH", tmp_path / "prod.db")
    from backend.app.models import application, job, resume_version  # noqa: F401
    SQLModel.metadata.create_all(prod_engine)


@pytest.fixture
def analytics_client(tmp_path, monkeypatch):
    """TestClient wired to a seeded, temporary analytics_demo.db."""
    _patch_production_db(tmp_path, monkeypatch)

    db_path = tmp_path / "analytics_demo.db"
    _seed_analytics_db(db_path)
    test_engine = create_engine(f"sqlite:///{db_path}", echo=False)
    monkeypatch.setattr("backend.app.analytics_db.ANALYTICS_DB_PATH", db_path)
    monkeypatch.setattr("backend.app.analytics_db.analytics_engine", test_engine)
    monkeypatch.setattr("backend.app.routers.analytics.analytics_engine", test_engine)

    from backend.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestAnalyticsAPI:
    def test_funnel_conditional_aggregation(self, analytics_client):
        r = analytics_client.get("/api/analytics/funnel")
        assert r.status_code == 200
        data = r.json()
        assert data[0]["source"] == "seek"
        assert data[0]["applied"] == 1
        assert data[0]["total"] == 1

    def test_skill_gaps_json_extraction(self, analytics_client):
        r = analytics_client.get("/api/analytics/skill-gaps")
        assert r.status_code == 200
        assert {"skill": "Airflow", "count": 1} in r.json()

    def test_score_distribution(self, analytics_client):
        r = analytics_client.get("/api/analytics/score-distribution")
        assert r.status_code == 200
        data = r.json()
        assert "histogram" in data and "by_source" in data
        assert data["by_source"][0]["source"] == "seek"

    def test_discovery_trend_has_moving_average(self, analytics_client):
        r = analytics_client.get("/api/analytics/discovery-trend")
        assert r.status_code == 200
        data = r.json()
        assert data[0]["moving_avg_7d"] == data[0]["jobs_found"]

    def test_conversion_by_score_bucket(self, analytics_client):
        r = analytics_client.get("/api/analytics/conversion")
        assert r.status_code == 200
        data = r.json()
        bucket = next(row for row in data if row["score_bucket"] == "60-79%")
        assert bucket["total_jobs"] == 1
        assert bucket["applications"] == 1
        assert bucket["conversion_pct"] == 100.0

    def test_top_companies(self, analytics_client):
        r = analytics_client.get("/api/analytics/top-companies")
        assert r.status_code == 200
        data = r.json()
        assert data[0]["company"] == "Acme Corp"
        assert data[0]["job_count"] == 1


class TestAnalyticsMissingDb:
    def test_returns_404_when_demo_db_missing(self, tmp_path, monkeypatch):
        _patch_production_db(tmp_path, monkeypatch)

        missing_path = tmp_path / "does_not_exist.db"
        test_engine = create_engine(f"sqlite:///{missing_path}", echo=False)
        monkeypatch.setattr("backend.app.analytics_db.ANALYTICS_DB_PATH", missing_path)
        monkeypatch.setattr("backend.app.analytics_db.analytics_engine", test_engine)
        monkeypatch.setattr("backend.app.routers.analytics.analytics_engine", test_engine)

        from backend.app.main import app
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/api/analytics/funnel")
        assert r.status_code == 404
        assert "generate_analytics_demo_data.py" in r.json()["detail"]
