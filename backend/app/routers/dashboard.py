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


@router.get("/dashboard/advisor")
def get_advisor_report() -> dict:
    """Generate advisor report with job analysis and recommendations."""
    from sqlmodel import Session, func, select
    from backend.app.database import engine
    from backend.app.models.job import Job
    from backend.app.models.application import Application
    from datetime import datetime
    
    with Session(engine) as session:
        jobs = session.exec(select(Job)).all()
        applications = session.exec(select(Application)).all()
        
        # Analyze skill gaps from all jobs
        all_missing: dict[str, int] = {}
        all_present: dict[str, int] = {}
        
        for job in jobs:
            gap = job.gap_analysis or {}
            for skill in gap.get("missing_skills", []):
                all_missing[skill.lower()] = all_missing.get(skill.lower(), 0) + 1
            for skill in gap.get("strong_matches", []):
                all_present[skill.lower()] = all_present.get(skill.lower(), 0) + 1
        
        top_missing = sorted(
            [{"skill": k, "count": v} for k, v in all_missing.items()],
            key=lambda x: x["count"], reverse=True
        )[:10]
        top_present = sorted(
            [{"skill": k, "count": v} for k, v in all_present.items()],
            key=lambda x: x["count"], reverse=True
        )[:8]
        
        # App stats
        app_stats = {
            "applied": len([a for a in applications if a.status == "applied"]),
            "responded": len([a for a in applications if a.status == "responded"]),
            "interviews": len([a for a in applications if a.status == "interview"]),
            "response_rate": f"{len([a for a in applications if a.status in ['responded', 'interview']]) / max(len(applications), 1) * 100:.1f}%"
        }
    
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "total_jobs_analysed": len(jobs),
        "top_missing_skills": top_missing,
        "top_present_skills": top_present,
        "app_stats": app_stats,
        "market_summary": f"Analysed {len(jobs)} jobs. Focus on strengthening: {', '.join([s['skill'] for s in top_missing[:3]]) if top_missing else 'N/A'}.",
        "skill_gap_analysis": f"Your strong matches: {', '.join([s['skill'] for s in top_present[:5]]) if top_present else 'N/A'}. Missing skills appear in {sum(s['count'] for s in top_missing)} job postings.",
        "recommended_actions": [
            "Review job descriptions with high match scores to understand what works",
            f"Consider learning: {', '.join([s['skill'] for s in top_missing[:3]])}" if top_missing else "Continue building current skill set",
            "Track application responses to identify patterns"
        ]
    }


@router.get("/dashboard/followups")
def get_followups() -> list[dict]:
    """Get applications that need follow-up."""
    from sqlmodel import Session, select
    from backend.app.database import engine
    from backend.app.models.application import Application
    from backend.app.models.job import Job
    from datetime import date
    from fastapi.encoders import jsonable_encoder
    
    with Session(engine) as session:
        apps = session.exec(select(Application)).all()
        jobs = {j.id: j for j in session.exec(select(Job)).all()}
        
        today = date.today()
        due = [
            {
                "application": jsonable_encoder(a),
                "job": jsonable_encoder(jobs.get(a.job_id)),
                "overdue_days": (today - a.follow_up_date).days if a.follow_up_date else 0
            }
            for a in apps
            if a.follow_up_date and a.follow_up_date <= today
        ]
    
    return sorted(due, key=lambda x: x["overdue_days"], reverse=True)
