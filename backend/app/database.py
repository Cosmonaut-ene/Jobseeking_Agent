"""Database setup — SQLite via SQLModel."""
from pathlib import Path
from sqlmodel import Session, SQLModel, create_engine
from backend.app.config import DB_PATH

DB_PATH.parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

def init_db() -> None:
    from backend.app.models import application, job, resume_version  # noqa: F401
    SQLModel.metadata.create_all(engine)
    _migrate(engine)


def _migrate(eng) -> None:
    """Idempotent schema migrations for columns added after initial release."""
    migrations = [
        "ALTER TABLE job ADD COLUMN notification_sent INTEGER NOT NULL DEFAULT 0",
    ]
    import sqlite3
    with sqlite3.connect(eng.url.database) as conn:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(job)")}
        for sql in migrations:
            col = sql.split("ADD COLUMN")[1].split()[0]
            if col not in existing:
                conn.execute(sql)

def get_session() -> Session:
    return Session(engine)
