"""Database setup — SQLite via SQLModel."""
from pathlib import Path
from sqlmodel import Session, SQLModel, create_engine, text
from backend.app.config import DB_PATH

DB_PATH.parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

def init_db() -> None:
    from backend.app.models import application, job, resume_version  # noqa: F401
    SQLModel.metadata.create_all(engine)
    _migrate_legacy_application_status()

def _migrate_legacy_application_status() -> None:
    """SPEC 附录 F.6 TASK-D01：Application.status 从自由字符串改为枚举前，
    存量记录都是 "pending"，映射为新枚举的 "ready"（AI 已备好、尚未确认投递）。

    幂等——每次启动都跑，只影响还残留 "pending" 的行，不会重复处理。
    没有 Alembic 之类的迁移工具，这是当前项目对该缺口的已知取舍（见 §8.5）。
    """
    with Session(engine) as session:
        session.exec(text("UPDATE application SET status = 'ready' WHERE status = 'pending'"))
        session.commit()

def get_session() -> Session:
    return Session(engine)
