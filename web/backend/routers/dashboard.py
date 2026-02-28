import os
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session, select

from jobseeking_agent.agents.advisor import AdvisorAgent
from jobseeking_agent.db import engine
from jobseeking_agent.models.application import Application, ApplicationStatus
from jobseeking_agent.models.job import Job, JobStatus
from jobseeking_agent.models.user_profile import UserProfile

router = APIRouter(tags=["dashboard"])

PROFILE_PATH = Path("data/user_profile.json")


def _require_api_key() -> None:
    if not os.environ.get("GEMINI_API_KEY"):
        raise HTTPException(
            400,
            detail="GEMINI_API_KEY not configured. Go to Settings to add your API key.",
        )


@router.get("/dashboard/stats")
def get_stats() -> dict:
    with Session(engine) as session:
        jobs = session.exec(select(Job)).all()
        apps = session.exec(select(Application)).all()

    counts = {s.value: 0 for s in JobStatus}
    for job in jobs:
        counts[job.status.value] += 1

    return {
        "job_counts": counts,
        "total_jobs": len(jobs),
        "total_applications": len(apps),
    }


@router.get("/dashboard/followups")
def get_followups() -> list[dict]:
    """Applications whose follow-up date has arrived and are still submitted."""
    today = date.today()
    with Session(engine) as session:
        apps = session.exec(select(Application)).all()
        jobs = {j.id: j for j in session.exec(select(Job)).all()}

    due = []
    for app in apps:
        if app.follow_up_date and app.follow_up_date <= today and app.status == ApplicationStatus.submitted:
            job = jobs.get(app.job_id)
            due.append({
                "application": jsonable_encoder(app),
                "job_title": job.title if job else "",
                "company": job.company if job else "",
            })

    return due


@router.post("/dashboard/advisor")
def run_advisor() -> dict:
    _require_api_key()
    try:
        profile = UserProfile.load(PROFILE_PATH)
    except FileNotFoundError:
        raise HTTPException(400, "User profile not found. Please set up your profile first.")

    with Session(engine) as session:
        jobs = list(session.exec(select(Job)).all())
        apps = list(session.exec(select(Application)).all())

    if not jobs:
        raise HTTPException(400, "No jobs in database. Scout some jobs first.")

    try:
        agent = AdvisorAgent()
        report = agent.run(jobs, apps, profile)
        return {
            "generated_at": report.generated_at.isoformat(),
            "total_jobs_analysed": report.total_jobs_analysed,
            "top_missing_skills": report.top_missing_skills,
            "top_present_skills": report.top_present_skills,
            "app_stats": report.app_stats,
            "market_summary": report.market_summary,
            "skill_gap_analysis": report.skill_gap_analysis,
            "recommended_actions": report.recommended_actions,
        }
    except Exception as e:
        raise HTTPException(500, detail=str(e))
