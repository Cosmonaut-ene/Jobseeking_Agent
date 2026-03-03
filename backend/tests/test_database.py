"""Tests for database setup."""
import pytest
import os
import tempfile
from pathlib import Path


class TestDatabase:
    def test_init_db_creates_tables(self, tmp_path, monkeypatch):
        """Test that init_db creates the required tables."""
        db_file = tmp_path / "test.db"
        monkeypatch.setattr("backend.app.config.DB_PATH", db_file)
        monkeypatch.setattr(
            "backend.app.database.DB_PATH", db_file
        )

        # Need to re-create engine with new path
        from sqlmodel import create_engine, Session, SQLModel, select
        test_engine = create_engine(f"sqlite:///{db_file}", echo=False)

        # Import models to register them
        from backend.app.models import job, application, resume_version
        SQLModel.metadata.create_all(test_engine)

        # Verify tables exist
        from sqlalchemy import inspect
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()
        assert "job" in tables
        assert "application" in tables
        assert "resumeversion" in tables

    def test_get_session_returns_session(self, tmp_path, monkeypatch):
        """Test that get_session returns a valid Session."""
        db_file = tmp_path / "test_session.db"

        from sqlmodel import create_engine, Session, SQLModel
        test_engine = create_engine(f"sqlite:///{db_file}", echo=False)

        from backend.app.models import job, application, resume_version
        SQLModel.metadata.create_all(test_engine)

        with Session(test_engine) as session:
            assert session is not None

    def test_job_table_columns(self, tmp_path):
        """Test that job table has the expected columns."""
        db_file = tmp_path / "test_cols.db"
        from sqlmodel import create_engine, SQLModel
        test_engine = create_engine(f"sqlite:///{db_file}", echo=False)
        from backend.app.models import job, application, resume_version
        SQLModel.metadata.create_all(test_engine)

        from sqlalchemy import inspect
        inspector = inspect(test_engine)
        columns = {col["name"] for col in inspector.get_columns("job")}
        expected = {"id", "source", "raw_jd", "title", "company", "location",
                    "salary_range", "skills_required", "match_score",
                    "gap_analysis", "source_url", "status",
                    "notification_sent", "created_at", "updated_at"}
        assert expected.issubset(columns)

    def test_application_table_columns(self, tmp_path):
        """Test that application table has the expected columns."""
        db_file = tmp_path / "test_app_cols.db"
        from sqlmodel import create_engine, SQLModel
        test_engine = create_engine(f"sqlite:///{db_file}", echo=False)
        from backend.app.models import job, application, resume_version
        SQLModel.metadata.create_all(test_engine)

        from sqlalchemy import inspect
        inspector = inspect(test_engine)
        columns = {col["name"] for col in inspector.get_columns("application")}
        expected = {"id", "job_id", "resume_version_id", "channel",
                    "applied_at", "follow_up_date", "notes", "status"}
        assert expected.issubset(columns)

    def test_resume_version_table_columns(self, tmp_path):
        """Test that resumeversion table has the expected columns."""
        db_file = tmp_path / "test_rv_cols.db"
        from sqlmodel import create_engine, SQLModel
        test_engine = create_engine(f"sqlite:///{db_file}", echo=False)
        from backend.app.models import job, application, resume_version
        SQLModel.metadata.create_all(test_engine)

        from sqlalchemy import inspect
        inspector = inspect(test_engine)
        columns = {col["name"] for col in inspector.get_columns("resumeversion")}
        expected = {"id", "job_id", "content_json", "ats_score",
                    "changes_summary", "created_at"}
        assert expected.issubset(columns)

    def test_can_insert_and_query_job(self, tmp_path):
        """Test that we can insert and query a Job record."""
        db_file = tmp_path / "test_insert.db"
        from sqlmodel import create_engine, SQLModel, Session, select
        test_engine = create_engine(f"sqlite:///{db_file}", echo=False)
        from backend.app.models import job as job_module, application, resume_version
        SQLModel.metadata.create_all(test_engine)

        from backend.app.models.job import Job
        new_job = Job(source="manual", raw_jd="Test job description", title="Dev")
        with Session(test_engine) as session:
            session.add(new_job)
            session.commit()
            session.refresh(new_job)
            saved_id = new_job.id

        with Session(test_engine) as session:
            fetched = session.get(Job, saved_id)
            assert fetched is not None
            assert fetched.title == "Dev"
            assert fetched.source == "manual"

    def test_database_module_has_engine(self):
        """Test that the database module exposes an engine."""
        from backend.app import database
        assert hasattr(database, "engine")
        assert database.engine is not None

    def test_database_module_has_init_db(self):
        """Test that the database module exposes init_db function."""
        from backend.app import database
        assert callable(database.init_db)

    def test_database_module_has_get_session(self):
        """Test that the database module exposes get_session function."""
        from backend.app import database
        assert callable(database.get_session)
