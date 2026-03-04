"""Scraper scheduler — runs all scrapers and processes results with ScoutAgent."""
import logging
from typing import Any

from sqlmodel import Session, select

from backend.app.agents.scout import ScoutAgent
from backend.app import notifications
from backend.app.database import engine, get_session
from backend.app.models.job import Job, JobStatus
from backend.app.models.user_profile import UserProfile
from backend.app.scrapers.seek import SeekScraper
from backend.app.scrapers.indeed import IndeedScraper
from backend.app.scrapers.linkedin import LinkedInAutoScraper
from backend.app.config import DEFAULT_MAX_JOBS

logger = logging.getLogger(__name__)


def _existing_urls() -> set[str]:
    with Session(engine) as session:
        urls = session.exec(select(Job.source_url)).all()
    return set(u for u in urls if u)


def run_daily_scout(settings: dict | None = None) -> dict[str, Any]:
    """
    Run all scrapers, score with ScoutAgent, send daily summary.
    settings: optional dict with scraper config (roles, locations, etc.)
    Returns stats dict.
    """
    settings = settings or {}

    try:
        profile = UserProfile.load()
    except FileNotFoundError:
        logger.error("[Scheduler] User profile not found — aborting daily scout.")
        return {"error": "User profile not found"}

    roles = settings.get("target_roles", profile.target_roles)
    locations = settings.get("locations", profile.preferences.locations or ["Australia"])
    max_jobs = settings.get("max_per_scraper", DEFAULT_MAX_JOBS)

    existing = _existing_urls()
    scout = ScoutAgent()
    stats: dict[str, int] = {"seek": 0, "indeed": 0, "linkedin": 0}
    high_jobs: list[Job] = []
    mid_jobs: list[Job] = []

    # --- Seek ---
    try:
        logger.info("[Scheduler] Starting Seek scraper...")
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
        logger.error("[Scheduler] Seek scraper failed: %s", e)

    # --- Indeed ---
    try:
        logger.info("[Scheduler] Starting Indeed scraper...")
        scraped = IndeedScraper().scrape(roles, locations, max_jobs, existing)
        stats["indeed"] = len(scraped)
        for sj in scraped:
            job = scout.run(
                raw_jd=sj.raw_jd,
                user_profile=profile,
                source="indeed",
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
        logger.error("[Scheduler] Indeed scraper failed: %s", e)

    # --- LinkedIn ---
    try:
        logger.info("[Scheduler] Starting LinkedIn scraper...")
        li_scraper = LinkedInAutoScraper()
        if li_scraper.has_cookies:
            scraped = li_scraper.scrape_search(roles, locations[0] if locations else "Australia", max_jobs, existing)
        else:
            logger.warning("[LinkedIn] No cookies — trying LinkedIn RSS fallback...")
            import asyncio
            from backend.app.scrapers.linkedin_rss import scrape_linkedin_rss
            try:
                scraped = asyncio.run(scrape_linkedin_rss(roles, locations[0] if locations else "Australia", max_jobs, existing))
                stats["linkedin_rss"] = len(scraped)
            except Exception as rss_err:
                logger.warning("[LinkedIn RSS] Fallback failed: %s", rss_err)
                scraped = []
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
        logger.error("[Scheduler] LinkedIn scraper failed: %s", e)

    # Send daily summary
    try:
        notifications.push_daily_summary(stats, high_jobs, mid_jobs)
    except Exception as e:
        logger.error("[Scheduler] Failed to send daily summary: %s", e)

    total_new = len(high_jobs) + len(mid_jobs)
    logger.info(
        "[Scheduler] Daily scout complete: seek=%d, indeed=%d, linkedin=%d, saved=%d (high=%d, mid=%d)",
        stats["seek"], stats["indeed"], stats["linkedin"],
        total_new, len(high_jobs), len(mid_jobs),
    )

    return {
        "scraped": stats,
        "saved": total_new,
        "high_score": len(high_jobs),
        "mid_score": len(mid_jobs),
    }
