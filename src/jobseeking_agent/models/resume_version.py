import uuid
from datetime import datetime
from typing import Any

from sqlmodel import JSON, Column, Field, SQLModel


class ResumeVersion(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    job_id: str = Field(index=True)
    content_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    ats_score: float = 0.0        # fraction of required skills covered
    changes_summary: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
