"""Dashboard stats router."""
from datetime import datetime, timedelta
from fastapi import APIRouter
from sqlmodel import Session, func, select
from backend.app.database import engine
from backend.app.models.job import Job, JobStatus

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/stats")
def get_stats() -> dict:
    with Session(engine) as session:
        total = session.exec(select(func.count(Job.id))).one()
        by_status: dict[str, int] = {}
        for status in JobStatus:
            count = session.exec(
                select(func.count(Job.id)).where(Job.status == status)
            ).one()
            by_status[status.value] = count

        # Score distribution
        high = session.exec(
            select(func.count(Job.id)).where(Job.match_score >= 0.8)
        ).one()
        mid = session.exec(
            select(func.count(Job.id)).where(Job.match_score >= 0.7).where(Job.match_score < 0.8)
        ).one()

        # Recent jobs (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent = session.exec(
            select(func.count(Job.id)).where(Job.created_at >= week_ago)
        ).one()

        # By source
        by_source: dict[str, int] = {}
        for source in ["seek", "indeed", "linkedin", "manual"]:
            count = session.exec(
                select(func.count(Job.id)).where(Job.source == source)
            ).one()
            if count > 0:
                by_source[source] = count

    return {
        "total_jobs": total,
        "by_status": by_status,
        "high_score_count": high,
        "mid_score_count": mid,
        "recent_jobs_7d": recent,
        "by_source": by_source,
    }


@router.get("/dashboard/recent-jobs")
def recent_jobs(limit: int = 10) -> list[dict]:
    from fastapi.encoders import jsonable_encoder
    with Session(engine) as session:
        jobs = session.exec(
            select(Job).order_by(Job.created_at.desc()).limit(limit)
        ).all()
    return jsonable_encoder(jobs)
