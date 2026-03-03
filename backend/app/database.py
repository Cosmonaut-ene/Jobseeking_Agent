"""Database setup — SQLite via SQLModel."""
from pathlib import Path
from sqlmodel import Session, SQLModel, create_engine
from backend.app.config import DB_PATH

DB_PATH.parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

def init_db() -> None:
    from backend.app.models import application, job, resume_version  # noqa: F401
    SQLModel.metadata.create_all(engine)

def get_session() -> Session:
    return Session(engine)
