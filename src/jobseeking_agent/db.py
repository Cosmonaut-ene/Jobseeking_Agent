from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

DB_PATH = Path("data/db/jobseeking.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


def init_db() -> None:
    # Import all models so SQLModel registers their tables before create_all
    from jobseeking_agent.models import job, resume_version  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine)
