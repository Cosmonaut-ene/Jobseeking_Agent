"""Batch scrape — runs all scrapers and processes results with ScoutAgent.

Manually triggered only (SPEC 附录 F.8 TASK-A01) — no background scheduler.
Was `scrapers/scheduler.py::run_daily_scout()` before the desktop-packaging
decision to drop APScheduler entirely (DECISIONS.md, F-CONF-02); renamed to
remove the "daily"/"scheduler" framing since neither is true anymore.
"""
import logging
from typing import Any

from sqlmodel import Session, select

from backend.app.agents.scout import ScoutAgent
from backend.app import notifications
from backend.app.database import engine
from backend.app.models.job import Job
from backend.app.models.user_profile import UserProfile
from backend.app.scrapers.seek import SeekScraper
from backend.app.config import DEFAULT_MAX_JOBS

logger = logging.getLogger(__name__)


def _existing_urls() -> set[str]:
    with Session(engine) as session:
        urls = session.exec(select(Job.source_url)).all()
    return set(u for u in urls if u)


def run_batch_scrape(settings: dict | None = None) -> dict[str, Any]:
    """
    Run all scrapers, score with ScoutAgent, send a completion summary.
    settings: optional dict with scraper config (roles, locations, etc.)
    Returns stats dict.
    """
    settings = settings or {}

    try:
        profile = UserProfile.load()
    except FileNotFoundError:
        logger.error("[BatchScrape] User profile not found — aborting.")
        return {"error": "User profile not found"}

    roles = settings.get("target_roles", profile.target_roles)
    locations = settings.get("locations", profile.preferences.locations or ["Australia"])
    max_jobs = settings.get("max_per_scraper", DEFAULT_MAX_JOBS)

    existing = _existing_urls()
    scout = ScoutAgent()
    stats: dict[str, int] = {"seek": 0, "linkedin": 0}
    high_jobs: list[Job] = []
    mid_jobs: list[Job] = []

    # --- Seek ---
    try:
        logger.info("[BatchScrape] Starting Seek scraper...")
        scraped = SeekScraper().scrape(roles, locations, max_jobs, existing)
        stats["seek"] = len(scraped)
        for sj in scraped:
            job = scout.run(
                raw_jd=sj.raw_jd,
                user_profile=profile,
                source="seek",
                source_url=sj.url,
                title=sj.title,
                company=sj.company,
                location=sj.location,
                salary_range=sj.salary,
                auto_filter=True,
                notify=True,
            )
            if job:
                from backend.app.config import HIGH_SCORE_THRESHOLD
                if job.match_score >= HIGH_SCORE_THRESHOLD:
                    high_jobs.append(job)
                else:
                    mid_jobs.append(job)
    except Exception as e:
        logger.error("[BatchScrape] Seek scraper failed: %s", e)

    # --- LinkedIn ---
    try:
        import asyncio
        from backend.app.scrapers.linkedin_guest import scrape_linkedin_guest
        logger.info("[BatchScrape] Starting LinkedIn scraper...")
        scraped = asyncio.run(scrape_linkedin_guest(roles, locations[0] if locations else "Australia", max_jobs, existing))
        stats["linkedin"] = len(scraped)
        for sj in scraped:
            job = scout.run(
                raw_jd=sj.raw_jd,
                user_profile=profile,
                source="linkedin",
                source_url=sj.url,
                title=sj.title,
                company=sj.company,
                location=sj.location,
                auto_filter=True,
                notify=True,
            )
            if job:
                from backend.app.config import HIGH_SCORE_THRESHOLD
                if job.match_score >= HIGH_SCORE_THRESHOLD:
                    high_jobs.append(job)
                else:
                    mid_jobs.append(job)
    except Exception as e:
        logger.error("[BatchScrape] LinkedIn scraper failed: %s", e)

    # Send completion summary
    try:
        notifications.push_batch_scrape_summary(stats, high_jobs, mid_jobs)
    except Exception as e:
        logger.error("[BatchScrape] Failed to send summary: %s", e)

    total_new = len(high_jobs) + len(mid_jobs)
    logger.info(
        "[BatchScrape] Complete: seek=%d, linkedin=%d, saved=%d (high=%d, mid=%d)",
        stats["seek"], stats["linkedin"],
        total_new, len(high_jobs), len(mid_jobs),
    )

    return {
        "scraped": stats,
        "saved": total_new,
        "high_score": len(high_jobs),
        "mid_score": len(mid_jobs),
    }
