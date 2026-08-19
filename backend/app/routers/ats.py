"""ATS simulation router — SPEC 附录 F.5 TASK-C03."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from backend.app.ats.simulator import (
    find_latest_uploaded_resume,
    flatten_resume_version_text,
    simulate_ats,
)
from backend.app.config import RESUMES_DIR
from backend.app.database import engine
from backend.app.models.job import Job
from backend.app.models.resume_version import ResumeVersion
from backend.app.models.user_profile import UserProfile

router = APIRouter(tags=["ats"])


class SimulateRequest(BaseModel):
    resume_version_id: str


@router.post("/ats/simulate")
def simulate(req: SimulateRequest) -> dict:
    with Session(engine) as session:
        resume_version = session.get(ResumeVersion, req.resume_version_id)
        if not resume_version:
            raise HTTPException(404, detail="Resume version not found")

        job = session.get(Job, resume_version.job_id)
        if not job:
            raise HTTPException(404, detail="Associated job not found")

        resume_file = find_latest_uploaded_resume(RESUMES_DIR)
        if resume_file is None:
            raise HTTPException(
                400,
                detail="No uploaded resume file found. Upload your resume on the Profile page first.",
            )

        try:
            profile = UserProfile.load()
        except FileNotFoundError:
            raise HTTPException(400, detail="User profile not found.")

        ats_keywords = (job.gap_analysis or {}).get("resume_improvements", {}).get("ats_keywords", [])
        resume_text = flatten_resume_version_text(resume_version.content_json or {})
        llm_ats_pct = job.match_score * 100 if job.match_score else None

        report = simulate_ats(
            resume_file_path=resume_file,
            profile=profile,
            jd_text=job.raw_jd,
            ats_keywords=ats_keywords,
            resume_text=resume_text,
            llm_ats_pct=llm_ats_pct,
        )

        resume_version.deterministic_ats_score = report.deterministic_ats_score
        resume_version.ats_report = report.model_dump()
        session.add(resume_version)
        session.commit()

        return report.model_dump()
