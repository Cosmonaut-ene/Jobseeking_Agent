import uuid
from datetime import date, datetime, timezone
from enum import Enum
from sqlmodel import Field, SQLModel


class ApplicationChannel(str, Enum):
    email = "email"
    easy_apply = "easy_apply"
    manual = "manual"


class ApplicationStatus(str, Enum):
    """SPEC 附录 F.6 TASK-D01. ready(AI 已备好) → applied(人类已投递) → responded/interview/rejected。

    没有邮箱监听等自动推断机制（见 DECISIONS.md），状态流转只能靠人工在 App 内确认。
    """
    ready = "ready"
    applied = "applied"
    responded = "responded"
    interview = "interview"
    rejected = "rejected"


# 合法状态流转表——ready→applied→{responded,interview,rejected}，之后视为终态。
# 不在 SPEC 里明确定义更深的流转（如 responded→interview），先按最小范围实现。
APPLICATION_STATUS_TRANSITIONS: dict[ApplicationStatus, set[ApplicationStatus]] = {
    ApplicationStatus.ready: {ApplicationStatus.applied},
    ApplicationStatus.applied: {
        ApplicationStatus.responded,
        ApplicationStatus.interview,
        ApplicationStatus.rejected,
    },
    ApplicationStatus.responded: set(),
    ApplicationStatus.interview: set(),
    ApplicationStatus.rejected: set(),
}


class Application(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    job_id: str = Field(foreign_key="job.id")
    resume_version_id: str = Field(foreign_key="resumeversion.id")
    channel: ApplicationChannel = ApplicationChannel.easy_apply
    applied_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    follow_up_date: date | None = None
    notes: str = ""
    status: ApplicationStatus = ApplicationStatus.ready
