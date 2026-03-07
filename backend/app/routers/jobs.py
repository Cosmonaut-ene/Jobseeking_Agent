"""Jobs router."""
import os
from datetime import date, timedelta
from pathlib import Path

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
    result = jsonable_encoder(job)
    result["resume_versions"] = jsonable_encoder(versions)
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


@router.post("/jobs/{job_id}/tailor")
def tailor_job(job_id: str) -> dict:
    _require_api_key()
    profile = _load_profile()
    try:
        with Session(engine) as session:
            job = session.get(Job, job_id)
            if not job:
                raise HTTPException(404, "Job not found")
            agent = TailorAgent()
            resume_version = agent.run(job, profile)
            session.add(resume_version)
            session.commit()
            session.refresh(resume_version)
            result = jsonable_encoder(resume_version)
            # Generate PDF
            try:
                from backend.app.pdf_generator import generate_resume_pdf
                from backend.app.config import RESUMES_DIR
                template_path = Path(__file__).parents[3] / "templates" / "resume.html"
                output_path = RESUMES_DIR / f"tailored_{job_id}.pdf"
                generate_resume_pdf(resume_version.content_json or {}, profile, template_path, output_path)
                result["pdf_download_url"] = f"/api/files/{job_id}/resume.pdf"
            except Exception as pdf_err:
                import logging
                logging.getLogger(__name__).warning("PDF generation failed: %s", pdf_err)
            return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))


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
            # Record application
            application = Application(
                job_id=job.id,
                resume_version_id=rv.id,
                channel=ApplicationChannel.easy_apply,
                follow_up_date=date.today() + timedelta(days=7),
            )
            session.add(application)
            job.status = JobStatus.applied
            session.add(job)
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
