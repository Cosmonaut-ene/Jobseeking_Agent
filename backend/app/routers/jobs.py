"""Jobs router."""
import logging
import os
import threading
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.app.agents.cover_letter import CoverLetterAgent
from backend.app.agents.scout import ScoutAgent
from backend.app.agents.tailor import TailorAgent
from backend.app.database import engine
from backend.app.models.application import Application, ApplicationChannel
from backend.app.models.job import Job, JobStatus
from backend.app.models.resume_version import ResumeVersion
from backend.app.models.user_profile import UserProfile

router = APIRouter(tags=["jobs"])
_logger = logging.getLogger(__name__)

# 定制简历要跑 2~3 轮 LLM 调用，实测能超过 90 秒，同步返回会让前端只能显示
# 一个死的 "Tailoring…"。改成跟 scrapers.py / profile.py 一致的"内存任务字典
# + 后台线程 + 轮询 GET"模式，让每一轮结束都能上报真实进度。
_tailor_tasks: dict[str, dict[str, Any]] = {}


def _require_api_key() -> None:
    if not os.environ.get("GEMINI_API_KEY"):
        raise HTTPException(400, detail="GEMINI_API_KEY not configured.")


def _load_profile() -> UserProfile:
    try:
        return UserProfile.load()
    except FileNotFoundError:
        raise HTTPException(400, detail="User profile not found. Upload your resume on the Profile page.")


@router.get("/jobs")
def list_jobs(status: str | None = None, min_score: float | None = None) -> list[dict]:
    with Session(engine) as session:
        stmt = select(Job).order_by(Job.created_at.desc())
        if status:
            stmt = stmt.where(Job.status == status)
        if min_score is not None:
            stmt = stmt.where(Job.match_score >= min_score)
        jobs = session.exec(stmt).all()
    return jsonable_encoder(jobs)


@router.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        versions = session.exec(
            select(ResumeVersion)
            .where(ResumeVersion.job_id == job_id)
            .order_by(ResumeVersion.created_at.desc())
        ).all()
        # SPEC 附录 F.6 TASK-D02: 供 Jobs 页面判断"是否需要显示确认已投递按钮"
        application = session.exec(
            select(Application)
            .where(Application.job_id == job_id)
            .order_by(Application.applied_at.desc())
        ).first()
    result = jsonable_encoder(job)
    result["resume_versions"] = jsonable_encoder(versions)
    result["application"] = jsonable_encoder(application) if application else None
    return result


class ScoutRequest(BaseModel):
    raw_jd: str
    source: str = "manual"
    auto_filter: bool = False  # Manual scout usually doesn't auto-filter


@router.post("/jobs/scout")
def scout_job(req: ScoutRequest) -> dict:
    _require_api_key()
    profile = _load_profile()
    try:
        agent = ScoutAgent()
        job = agent.run(
            raw_jd=req.raw_jd,
            user_profile=profile,
            source=req.source,
            auto_filter=req.auto_filter,
            notify=False,  # Manual scout doesn't auto-push
        )
        if job is None:
            return {"filtered": True, "message": "Job score below threshold — not saved."}
        return jsonable_encoder(job)
    except Exception as e:
        raise HTTPException(500, detail=str(e))


class StatusUpdate(BaseModel):
    status: JobStatus


@router.put("/jobs/{job_id}/status")
def update_status(job_id: str, body: StatusUpdate) -> dict:
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        job.status = body.status
        session.add(job)
        session.commit()
        session.refresh(job)
        return jsonable_encoder(job)


@router.delete("/jobs/{job_id}")
def delete_job(job_id: str) -> dict:
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        session.delete(job)
        session.commit()
    return {"deleted": True}


def _run_tailor(task_id: str, job_id: str) -> None:
    _tailor_tasks[task_id].update(status="running", progress="Loading job and profile...")
    try:
        profile = UserProfile.load()
        with Session(engine) as session:
            job = session.get(Job, job_id)
            if not job:
                _tailor_tasks[task_id].update(status="error", progress="Job not found", error="Job not found")
                return
            agent = TailorAgent()

            def on_progress(round_num: int, max_iterations: int, deterministic_score: float) -> None:
                _tailor_tasks[task_id].update(
                    status="running",
                    progress=f"Round {round_num}/{max_iterations} — deterministic {deterministic_score:.0f}%",
                    round=round_num,
                    max_iterations=max_iterations,
                    deterministic_ats_score=deterministic_score,
                )

            # TailorAgent.run() persists every iteration round itself (SPEC 附录 F.5
            # TASK-C04 — 每轮版本均须落库保留，不得覆盖历史版本) and returns the
            # best-scoring, already-committed version. Do not re-add/commit it here.
            resume_version = agent.run(job, profile, on_progress=on_progress)
            result = jsonable_encoder(resume_version)
            try:
                from backend.app.pdf_generator import generate_resume_pdf
                from backend.app.config import RESUMES_DIR
                template_path = Path(__file__).parents[3] / "templates" / "resume.html"
                output_path = RESUMES_DIR / f"tailored_{job_id}.pdf"
                generate_resume_pdf(resume_version.content_json or {}, profile, template_path, output_path)
                result["pdf_download_url"] = f"/api/files/{job_id}/resume.pdf"
            except Exception as pdf_err:
                _logger.warning("PDF generation failed: %s", pdf_err)
            _tailor_tasks[task_id].update(status="done", progress="Done", result=result)
    except Exception as exc:
        _tailor_tasks[task_id].update(status="error", progress=str(exc), error=str(exc))


@router.post("/jobs/{job_id}/tailor")
def tailor_job(job_id: str) -> dict:
    _require_api_key()
    _load_profile()  # 提前校验 profile 存在，避免开了任务才发现失败
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
    task_id = str(uuid.uuid4())
    _tailor_tasks[task_id] = {"status": "pending", "progress": "Queued"}
    threading.Thread(target=_run_tailor, args=(task_id, job_id), daemon=True).start()
    return {"task_id": task_id}


@router.get("/jobs/{job_id}/tailor/tasks/{task_id}")
def get_tailor_task(job_id: str, task_id: str) -> dict:
    if task_id not in _tailor_tasks:
        raise HTTPException(404, "Task not found")
    return _tailor_tasks[task_id]


@router.get("/jobs/{job_id}/cover-letter")
def get_cover_letter(job_id: str) -> dict:
    from backend.app.config import COVER_LETTERS_DIR
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
    safe_company = "".join(c if c.isalnum() else "_" for c in job.company)
    safe_title = "".join(c if c.isalnum() else "_" for c in job.title)
    filename = f"{safe_company}_{safe_title}_{job_id[:8]}.txt"
    path = COVER_LETTERS_DIR / filename
    if not path.exists():
        raise HTTPException(404, "Cover letter not found")
    content = path.read_text(encoding="utf-8")
    first_line, _, rest = content.partition("\n\n")
    subject = first_line.removeprefix("Subject: ")
    return {"subject_line": subject, "body": rest}


@router.post("/jobs/{job_id}/cover-letter")
def generate_cover_letter(job_id: str) -> dict:
    _require_api_key()
    profile = _load_profile()
    try:
        with Session(engine) as session:
            job = session.get(Job, job_id)
            if not job:
                raise HTTPException(404, "Job not found")
            rv = session.exec(
                select(ResumeVersion)
                .where(ResumeVersion.job_id == job_id)
                .order_by(ResumeVersion.created_at.desc())
            ).first()
            if not rv:
                raise HTTPException(400, detail="No tailored resume found. Run Tailor first.")
            agent = CoverLetterAgent()
            subject, body = agent.generate(job, rv, profile)
            path = agent.save(job, subject, body)
            # Record application — status stays at its default (ready): drafting a
            # cover letter is not the same as actually submitting it. Job.status
            # must NOT flip to "applied" here — that used to happen and made the
            # status badge lie the instant this endpoint ran, well before the
            # human ever touched the actual job board. Job.status only becomes
            # "applied" when Application.status does, via the human-confirmed
            # PUT /api/applications/{id}/status transition (SPEC 附录 F.6 TASK-D02,
            # DECISIONS.md DEC-05 — reminder-only, confirmation always happens
            # in-app against a specific job, never silently on draft).
            application = Application(
                job_id=job.id,
                resume_version_id=rv.id,
                channel=ApplicationChannel.easy_apply,
                follow_up_date=date.today() + timedelta(days=7),
            )
            session.add(application)
            session.commit()
            session.refresh(application)
            return {
                "subject_line": subject,
                "body": body,
                "path": path,
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))
