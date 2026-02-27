import uuid
from datetime import date, datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class ApplicationChannel(str, Enum):
    email = "email"
    easy_apply = "easy_apply"
    manual = "manual"


class ApplicationStatus(str, Enum):
    submitted = "submitted"
    follow_up_sent = "follow_up_sent"
    response_received = "response_received"
    closed = "closed"


class Application(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    job_id: str = Field(index=True)
    resume_version_id: str
    channel: ApplicationChannel
    status: ApplicationStatus = ApplicationStatus.submitted
    applied_at: datetime = Field(default_factory=datetime.utcnow)
    follow_up_date: date | None = None
    notes: str = ""
