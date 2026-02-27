import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlmodel import JSON, Column, Field, SQLModel


class JobStatus(str, Enum):
    new = "new"
    reviewed = "reviewed"
    applied = "applied"
    interview = "interview"
    rejected = "rejected"
    offer = "offer"


class Job(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    source: str  # linkedin / seek / indeed / manual
    raw_jd: str
    title: str = ""
    company: str = ""
    location: str = ""
    salary_range: str = ""
    skills_required: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    match_score: float = 0.0
    gap_analysis: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    status: JobStatus = JobStatus.new
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
