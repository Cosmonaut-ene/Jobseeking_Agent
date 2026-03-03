"""Scrapers router — background scrape jobs."""
import os
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.app.agents.scout import ScoutAgent
from backend.app.database import engine
from backend.app.models.job import Job
from backend.app.models.user_profile import UserProfile
from backend.app.scrapers.linkedin import LinkedInAutoScraper
from backend.app.scrapers.seek import SeekScraper
from backend.app.scrapers.indeed import IndeedScraper

router = APIRouter(tags=["scrapers"])

_tasks: dict[str, dict[str, Any]] = {}
PROFILE_PATH = Path("data/user_profile.json")


def _require_api_key() -> None:
    if not os.environ.get("GEMINI_API_KEY"):
        raise HTTPException(400, detail="GEMINI_API_KEY not configured.")


def _existing_urls() -> set[str]:
    with Session(engine) as session:
        urls = session.exec(select(Job.source_url)).all()
    return set(u for u in urls if u)


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
        scraped = SeekScraper().scrape(roles, locations, max_per_query, existing)
        if not scraped:
            _tasks[task_id].update(status="done", progress="No new jobs found.", results=[])
            return
        scout = ScoutAgent()
        results: list[dict] = []
        for i, sj in enumerate(scraped):
            _tasks[task_id]["progress"] = f"Analysing {i+1}/{len(scraped)}: {sj.title or sj.url}"
            job = scout.run(raw_jd=sj.raw_jd, user_profile=profile, source="seek",
                            source_url=sj.url, title=sj.title, company=sj.company,
                            location=sj.location, salary_range=sj.salary,
                            auto_filter=True, notify=True)
            if job:
                results.append(jsonable_encoder(job))
        _tasks[task_id].update(status="done", progress=f"Done — {len(results)} job(s) saved.", results=results)
    except Exception as exc:
        _tasks[task_id].update(status="error", progress=str(exc), error=str(exc))


@router.post("/scrapers/seek")
def start_seek(req: SeekRequest) -> dict:
    _require_api_key()
    task_id = str(uuid.uuid4())
    _tasks[task_id] = {"status": "pending", "progress": "Queued"}
    threading.Thread(target=_run_seek, args=(task_id, req.roles, req.locations, req.max_per_query), daemon=True).start()
    return {"task_id": task_id}


class IndeedRequest(BaseModel):
    roles: list[str]
    locations: list[str]
    max_per_query: int = 10


def _run_indeed(task_id: str, roles: list[str], locations: list[str], max_per_query: int) -> None:
    _tasks[task_id].update(status="running", progress="Loading user profile...")
    try:
        profile = UserProfile.load(PROFILE_PATH)
        existing = _existing_urls()
        _tasks[task_id]["progress"] = "Starting Playwright browser..."
        scraped = IndeedScraper().scrape(roles, locations, max_per_query, existing)
        if not scraped:
            _tasks[task_id].update(status="done", progress="No new jobs found.", results=[])
            return
        scout = ScoutAgent()
        results: list[dict] = []
        for i, sj in enumerate(scraped):
            _tasks[task_id]["progress"] = f"Analysing {i+1}/{len(scraped)}: {sj.title or sj.url}"
            job = scout.run(raw_jd=sj.raw_jd, user_profile=profile, source="indeed",
                            source_url=sj.url, title=sj.title, company=sj.company,
                            location=sj.location, salary_range=sj.salary,
                            auto_filter=True, notify=True)
            if job:
                results.append(jsonable_encoder(job))
        _tasks[task_id].update(status="done", progress=f"Done — {len(results)} job(s) saved.", results=results)
    except Exception as exc:
        _tasks[task_id].update(status="error", progress=str(exc), error=str(exc))


@router.post("/scrapers/indeed")
def start_indeed(req: IndeedRequest) -> dict:
    _require_api_key()
    task_id = str(uuid.uuid4())
    _tasks[task_id] = {"status": "pending", "progress": "Queued"}
    threading.Thread(target=_run_indeed, args=(task_id, req.roles, req.locations, req.max_per_query), daemon=True).start()
    return {"task_id": task_id}


class LinkedInAutoRequest(BaseModel):
    keywords: list[str]
    location: str
    max_results: int = 25


class LinkedInURLRequest(BaseModel):
    urls: list[str]


def _run_linkedin_auto(task_id: str, keywords: list[str], location: str, max_results: int) -> None:
    _tasks[task_id].update(status="running", progress="Loading cookies...")
    try:
        profile = UserProfile.load(PROFILE_PATH)
        existing = _existing_urls()
        li = LinkedInAutoScraper()
        if not li.has_cookies:
            _tasks[task_id].update(status="error", progress="No LinkedIn cookies found. Upload cookies first.", error="No cookies")
            return
        _tasks[task_id]["progress"] = "Searching LinkedIn..."
        scraped = li.scrape_search(keywords, location, max_results, existing)
        if not scraped:
            _tasks[task_id].update(status="done", progress="No new jobs found.", results=[])
            return
        scout = ScoutAgent()
        results: list[dict] = []
        for i, sj in enumerate(scraped):
            _tasks[task_id]["progress"] = f"Analysing {i+1}/{len(scraped)}: {sj.title or sj.url}"
            job = scout.run(raw_jd=sj.raw_jd, user_profile=profile, source="linkedin",
                            source_url=sj.url, title=sj.title, company=sj.company,
                            location=sj.location, auto_filter=True, notify=True)
            if job:
                results.append(jsonable_encoder(job))
        _tasks[task_id].update(status="done", progress=f"Done — {len(results)} job(s) saved.", results=results)
    except Exception as exc:
        _tasks[task_id].update(status="error", progress=str(exc), error=str(exc))


@router.post("/scrapers/linkedin")
def start_linkedin(req: LinkedInAutoRequest) -> dict:
    _require_api_key()
    task_id = str(uuid.uuid4())
    _tasks[task_id] = {"status": "pending", "progress": "Queued"}
    threading.Thread(target=_run_linkedin_auto, args=(task_id, req.keywords, req.location, req.max_results), daemon=True).start()
    return {"task_id": task_id}


def _run_linkedin_urls(task_id: str, urls: list[str]) -> None:
    _tasks[task_id].update(status="running", progress="Loading user profile...")
    try:
        profile = UserProfile.load(PROFILE_PATH)
        existing = _existing_urls()
        li = LinkedInAutoScraper()
        _tasks[task_id]["progress"] = "Fetching job pages..."
        scraped = li.scrape_urls(urls, existing)
        if not scraped:
            _tasks[task_id].update(status="done", progress="No jobs extracted.", results=[])
            return
        scout = ScoutAgent()
        results: list[dict] = []
        for i, sj in enumerate(scraped):
            _tasks[task_id]["progress"] = f"Analysing {i+1}/{len(scraped)}: {sj.title or sj.url}"
            job = scout.run(raw_jd=sj.raw_jd, user_profile=profile, source="linkedin",
                            source_url=sj.url, title=sj.title, company=sj.company,
                            location=sj.location, auto_filter=True, notify=True)
            if job:
                results.append(jsonable_encoder(job))
        _tasks[task_id].update(status="done", progress=f"Done — {len(results)} job(s) saved.", results=results)
    except Exception as exc:
        _tasks[task_id].update(status="error", progress=str(exc), error=str(exc))


@router.post("/scrapers/linkedin-urls")
def start_linkedin_urls(req: LinkedInURLRequest) -> dict:
    _require_api_key()
    if not req.urls:
        raise HTTPException(400, "No URLs provided.")
    task_id = str(uuid.uuid4())
    _tasks[task_id] = {"status": "pending", "progress": "Queued"}
    threading.Thread(target=_run_linkedin_urls, args=(task_id, req.urls), daemon=True).start()
    return {"task_id": task_id}


@router.get("/tasks/{task_id}")
def get_task(task_id: str) -> dict:
    if task_id not in _tasks:
        raise HTTPException(404, "Task not found")
    return _tasks[task_id]
