"""
Scrapers router — long-running scrape jobs via background threads + polling.

Pattern:
  POST /api/scrapers/seek      → {task_id}
  POST /api/scrapers/linkedin  → {task_id}
  GET  /api/tasks/{task_id}    → {status, progress, results?, error?}
"""

import os
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlmodel import Session, select

from jobseeking_agent.agents.scout import ScoutAgent
from jobseeking_agent.db import engine
from jobseeking_agent.models.job import Job
from jobseeking_agent.models.user_profile import UserProfile
from jobseeking_agent.scrapers.linkedin import LinkedInScraper
from jobseeking_agent.scrapers.seek import SeekScraper

router = APIRouter(tags=["scrapers"])

# In-memory task store {task_id: {status, progress, results?, error?}}
_tasks: dict[str, dict[str, Any]] = {}

PROFILE_PATH = Path("data/user_profile.json")


def _require_api_key() -> None:
    if not os.environ.get("GEMINI_API_KEY"):
        raise HTTPException(
            400,
            detail="GEMINI_API_KEY not configured. Go to Settings to add your API key.",
        )


def _existing_urls() -> set[str]:
    with Session(engine) as session:
        urls = session.exec(select(Job.source_url)).all()
    return set(urls)


# ── Seek ─────────────────────────────────────────────────────────────────────

class SeekRequest(BaseModel):
    roles: list[str]
    locations: list[str]
    max_per_query: int = 10


def _run_seek(task_id: str, roles: list[str], locations: list[str], max_per_query: int) -> None:
    _tasks[task_id].update(status="running", progress="Loading user profile...")
    try:
        profile = UserProfile.load(PROFILE_PATH)
        existing = _existing_urls()

        _tasks[task_id]["progress"] = "Starting Playwright browser..."
        scraper = SeekScraper()
        scraped = scraper.scrape(roles, locations, max_per_query, existing)

        if not scraped:
            _tasks[task_id].update(status="done", progress="No new jobs found.", results=[])
            return

        scout = ScoutAgent()
        results: list[dict] = []
        for i, sj in enumerate(scraped):
            _tasks[task_id]["progress"] = f"Analysing job {i + 1}/{len(scraped)}: {sj.title or sj.url}"
            job = scout.run(
                raw_jd=sj.raw_jd,
                user_profile=profile,
                source="seek",
                source_url=sj.url,
                title=sj.title,
                company=sj.company,
                location=sj.location,
                salary_range=sj.salary,
            )
            results.append(jsonable_encoder(job))

        _tasks[task_id].update(
            status="done",
            progress=f"Done — {len(results)} new job(s) added.",
            results=results,
        )
    except Exception as exc:
        _tasks[task_id].update(status="error", progress=str(exc), error=str(exc))


@router.post("/scrapers/seek")
def start_seek(req: SeekRequest) -> dict:
    _require_api_key()
    task_id = str(uuid.uuid4())
    _tasks[task_id] = {"status": "pending", "progress": "Queued"}
    t = threading.Thread(
        target=_run_seek,
        args=(task_id, req.roles, req.locations, req.max_per_query),
        daemon=True,
    )
    t.start()
    return {"task_id": task_id}


# ── LinkedIn ─────────────────────────────────────────────────────────────────

class LinkedInRequest(BaseModel):
    urls: list[str]


def _run_linkedin(task_id: str, urls: list[str]) -> None:
    _tasks[task_id].update(status="running", progress="Loading user profile...")
    try:
        profile = UserProfile.load(PROFILE_PATH)
        existing = _existing_urls()
        new_urls = [u for u in urls if u.strip() and u not in existing]

        if not new_urls:
            _tasks[task_id].update(status="done", progress="All URLs already processed.", results=[])
            return

        # Write URLs to a temp file for LinkedInScraper.scrape_from_file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
            tmp.write("\n".join(new_urls))
            tmp_path = Path(tmp.name)

        _tasks[task_id]["progress"] = "Starting Playwright browser..."
        try:
            scraper = LinkedInScraper()
            scraped = scraper.scrape_from_file(tmp_path, existing_urls=existing)
        finally:
            tmp_path.unlink(missing_ok=True)

        if not scraped:
            _tasks[task_id].update(status="done", progress="No jobs extracted.", results=[])
            return

        scout = ScoutAgent()
        results: list[dict] = []
        for i, sj in enumerate(scraped):
            _tasks[task_id]["progress"] = f"Analysing job {i + 1}/{len(scraped)}: {sj.title or sj.url}"
            job = scout.run(
                raw_jd=sj.raw_jd,
                user_profile=profile,
                source="linkedin",
                source_url=sj.url,
                title=sj.title,
                company=sj.company,
                location=sj.location,
            )
            results.append(jsonable_encoder(job))

        _tasks[task_id].update(
            status="done",
            progress=f"Done — {len(results)} new job(s) added.",
            results=results,
        )
    except Exception as exc:
        _tasks[task_id].update(status="error", progress=str(exc), error=str(exc))


@router.post("/scrapers/linkedin")
def start_linkedin(req: LinkedInRequest) -> dict:
    _require_api_key()
    if not req.urls:
        raise HTTPException(400, "No URLs provided.")
    task_id = str(uuid.uuid4())
    _tasks[task_id] = {"status": "pending", "progress": "Queued"}
    t = threading.Thread(
        target=_run_linkedin,
        args=(task_id, req.urls),
        daemon=True,
    )
    t.start()
    return {"task_id": task_id}


# ── Task polling ─────────────────────────────────────────────────────────────

@router.get("/tasks/{task_id}")
def get_task(task_id: str) -> dict:
    if task_id not in _tasks:
        raise HTTPException(404, "Task not found")
    return _tasks[task_id]
