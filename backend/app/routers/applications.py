"""Applications router — status transitions (SPEC 附录 F.6 TASK-D01/D02)."""
from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.app import notifications
from backend.app.database import engine
from backend.app.models.application import (
    APPLICATION_STATUS_TRANSITIONS,
    Application,
    ApplicationStatus,
)
from backend.app.models.job import Job, JobStatus

router = APIRouter(tags=["applications"])


class StatusUpdateRequest(BaseModel):
    status: ApplicationStatus


@router.put("/applications/{application_id}/status")
def update_status(application_id: str, body: StatusUpdateRequest) -> dict:
    with Session(engine) as session:
        application = session.get(Application, application_id)
        if not application:
            raise HTTPException(404, detail="Application not found")

        allowed = APPLICATION_STATUS_TRANSITIONS.get(application.status, set())
        if body.status != application.status and body.status not in allowed:
            raise HTTPException(
                400,
                detail=f"Cannot transition Application from '{application.status.value}' "
                       f"to '{body.status.value}'",
            )

        application.status = body.status
        session.add(application)
        # Job.status only becomes "applied" at this exact human-confirmed moment
        # — not when a cover letter is merely drafted (see routers/jobs.py::
        # generate_cover_letter). This is the single place the status badge
        # shown throughout the UI is allowed to say "applied".
        if body.status == ApplicationStatus.applied:
            job = session.get(Job, application.job_id)
            if job:
                job.status = JobStatus.applied
                session.add(job)
        session.commit()
        session.refresh(application)
        return jsonable_encoder(application)


@router.get("/applications")
def list_applications(status: ApplicationStatus | None = None) -> list[dict]:
    with Session(engine) as session:
        stmt = select(Application).order_by(Application.applied_at.desc())
        if status:
            stmt = stmt.where(Application.status == status)
        applications = session.exec(stmt).all()
    return jsonable_encoder(applications)


@router.post("/applications/push-reminder")
def push_reminder() -> dict:
    """批量推送"待确认投递"提醒——纯提醒文案，不含任何可执行的确认操作
    （SPEC 附录 F.6 TASK-D02，DECISIONS.md DEC-05：消息内一键确认已否决，
    确认动作固定在 App 内针对具体 Job 完成）。"""
    with Session(engine) as session:
        ready_applications = session.exec(
            select(Application).where(Application.status == ApplicationStatus.ready)
        ).all()
        jobs_by_id = {}
        if ready_applications:
            from backend.app.models.job import Job

            job_ids = [a.job_id for a in ready_applications]
            jobs_by_id = {j.id: j for j in session.exec(select(Job).where(Job.id.in_(job_ids))).all()}

    if not ready_applications:
        return {"sent": False, "reason": "No applications pending confirmation.", "count": 0}

    sent = notifications.push_ready_applications_reminder(ready_applications, jobs_by_id)
    return {"sent": sent, "count": len(ready_applications)}
