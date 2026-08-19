"""Tests for the legacy Application.status migration (SPEC 附录 F.6 TASK-D01)."""
from sqlmodel import Session, SQLModel, create_engine, select, text


def _make_engine(tmp_path):
    db_file = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_file}", echo=False)
    from backend.app.models import application, job, resume_version  # noqa: F401
    SQLModel.metadata.create_all(engine)
    return engine


def test_legacy_pending_rows_migrated_to_ready(tmp_path, monkeypatch):
    from backend.app.database import _migrate_legacy_application_status
    from backend.app.models.application import Application, ApplicationStatus
    from backend.app.models.job import Job
    from backend.app.models.resume_version import ResumeVersion

    engine = _make_engine(tmp_path)
    monkeypatch.setattr("backend.app.database.engine", engine)

    with Session(engine) as session:
        job = Job(source="manual", raw_jd="JD")
        rv = ResumeVersion(job_id=job.id, content_json={})
        session.add(job)
        session.add(rv)
        session.commit()
        session.refresh(job)
        session.refresh(rv)

        # Bypass the Python enum entirely — simulate a pre-migration row the old
        # free-string column allowed, which ApplicationStatus would now reject.
        session.exec(
            text(
                "INSERT INTO application (id, job_id, resume_version_id, channel, "
                "applied_at, notes, status) VALUES "
                "('legacy-1', :job_id, :rv_id, 'easy_apply', '2026-01-01T00:00:00', '', 'pending')"
            ),
            params={"job_id": job.id, "rv_id": rv.id},
        )
        session.commit()

    _migrate_legacy_application_status()

    with Session(engine) as session:
        migrated = session.get(Application, "legacy-1")
        assert migrated.status == ApplicationStatus.ready


def test_migration_is_idempotent_and_leaves_other_statuses_untouched(tmp_path, monkeypatch):
    from backend.app.database import _migrate_legacy_application_status
    from backend.app.models.application import Application, ApplicationStatus
    from backend.app.models.job import Job
    from backend.app.models.resume_version import ResumeVersion

    engine = _make_engine(tmp_path)
    monkeypatch.setattr("backend.app.database.engine", engine)

    with Session(engine) as session:
        job = Job(source="manual", raw_jd="JD")
        rv = ResumeVersion(job_id=job.id, content_json={})
        session.add(job)
        session.add(rv)
        session.commit()
        session.refresh(job)
        session.refresh(rv)

        already_applied = Application(job_id=job.id, resume_version_id=rv.id, status=ApplicationStatus.applied)
        session.add(already_applied)
        session.commit()
        applied_id = already_applied.id

    _migrate_legacy_application_status()
    _migrate_legacy_application_status()  # run twice — must not change an already-correct row

    with Session(engine) as session:
        untouched = session.get(Application, applied_id)
        assert untouched.status == ApplicationStatus.applied
