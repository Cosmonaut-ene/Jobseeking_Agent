import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlmodel import Session, select

from jobseeking_agent.agents.applier import ApplierAgent
from jobseeking_agent.agents.scout import ScoutAgent
from jobseeking_agent.agents.tailor import TailorAgent
from jobseeking_agent.db import engine
from jobseeking_agent.models.application import Application, ApplicationChannel
from jobseeking_agent.models.job import Job, JobStatus
from jobseeking_agent.models.resume_version import ResumeVersion
from jobseeking_agent.models.user_profile import UserProfile

router = APIRouter(tags=["jobs"])

PROFILE_PATH = Path("data/user_profile.json")


def _require_api_key() -> None:
    if not os.environ.get("GEMINI_API_KEY"):
        raise HTTPException(
            400,
            detail="GEMINI_API_KEY not configured. Go to Settings to add your API key.",
        )


def _load_profile() -> UserProfile:
    try:
        return UserProfile.load(PROFILE_PATH)
    except FileNotFoundError:
        raise HTTPException(
            400,
            detail="User profile not found. Please upload your resume on the Resume page first.",
        )


# ── List / Get ──────────────────────────────────────────────────────────────

@router.get("/jobs")
def list_jobs(status: str | None = None) -> list[dict]:
    with Session(engine) as session:
        stmt = select(Job).order_by(Job.created_at.desc())
        if status:
            stmt = stmt.where(Job.status == status)
        jobs = session.exec(stmt).all()
    return jsonable_encoder(jobs)


@router.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        # Attach resume versions
        versions = session.exec(
            select(ResumeVersion)
            .where(ResumeVersion.job_id == job_id)
            .order_by(ResumeVersion.created_at.desc())
        ).all()
    result = jsonable_encoder(job)
    result["resume_versions"] = jsonable_encoder(versions)
    return result


# ── Scout ───────────────────────────────────────────────────────────────────

class ScoutRequest(BaseModel):
    raw_jd: str
    source: str = "manual"


@router.post("/jobs/scout")
def scout_job(req: ScoutRequest) -> dict:
    _require_api_key()
    profile = _load_profile()
    try:
        agent = ScoutAgent()
        job = agent.run(raw_jd=req.raw_jd, user_profile=profile, source=req.source)
        return jsonable_encoder(job)
    except Exception as e:
        raise HTTPException(500, detail=str(e))


# ── Status update ───────────────────────────────────────────────────────────

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


# ── Tailor ──────────────────────────────────────────────────────────────────

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
            return jsonable_encoder(resume_version)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))


# ── Apply ───────────────────────────────────────────────────────────────────

@router.post("/jobs/{job_id}/apply")
def apply_job(job_id: str) -> dict:
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
                raise HTTPException(
                    400,
                    detail="No tailored resume found. Run Tailor first.",
                )

            agent = ApplierAgent()
            application, cover_letter_path = agent.run(
                job, rv, profile, ApplicationChannel.easy_apply
            )
            session.add(application)
            job.status = JobStatus.applied
            session.add(job)
            session.commit()
            session.refresh(application)

            result = jsonable_encoder(application)
            result["cover_letter_path"] = cover_letter_path
            # Also return the text so the frontend can display it without file access
            if cover_letter_path:
                try:
                    result["cover_letter_text"] = Path(cover_letter_path).read_text(encoding="utf-8")
                except Exception:
                    result["cover_letter_text"] = None
            else:
                result["cover_letter_text"] = None
            return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))
