import uuid
from datetime import date, datetime
from enum import Enum
from sqlmodel import Field, SQLModel


class ApplicationChannel(str, Enum):
    email = "email"
    easy_apply = "easy_apply"
    manual = "manual"


class Application(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    job_id: str = Field(foreign_key="job.id")
    resume_version_id: str = Field(foreign_key="resumeversion.id")
    channel: ApplicationChannel = ApplicationChannel.easy_apply
    applied_at: datetime = Field(default_factory=datetime.utcnow)
    follow_up_date: date | None = None
    notes: str = ""
    status: str = "pending"
