import uuid
from datetime import datetime, timezone
from typing import Any
from sqlmodel import JSON, Column, Field, SQLModel


class ResumeVersion(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    job_id: str = Field(foreign_key="job.id")
    content_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    ats_score: float = 0.0  # LLM 定性估算（Gemini），见 SPEC §8.6 已知局限
    changes_summary: str = ""
    # 确定性 ATS 模拟结果（SPEC 附录 F.5 TASK-C03）——与 ats_score 并存，不互相覆盖
    deterministic_ats_score: float = 0.0
    ats_report: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
