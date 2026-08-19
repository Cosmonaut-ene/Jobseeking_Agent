"""Profile router — manage user profile JSON."""
import asyncio
import json
import logging
import os
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from backend.app.agents.parser import ResumeParser
from backend.app.agents.profile_sync import apply_skill_diff, build_skill_diff, sync_profile
from backend.app.models.user_profile import UserProfile
from backend.app.config import PROFILE_PATH, RESUMES_DIR

logger = logging.getLogger(__name__)
router = APIRouter(tags=["profile"])

# GitHub sync 任务状态，跟 routers/scrapers.py 用的是同一套内存字典 + 后台线程模式
_github_sync_tasks: dict[str, dict[str, Any]] = {}


@router.get("/profile")
def get_profile() -> dict:
    try:
        profile = UserProfile.load()
        return profile.model_dump()
    except FileNotFoundError:
        return {}


@router.put("/profile")
def update_profile(data: dict) -> dict:
    """Save user profile JSON directly."""
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"saved": True}


@router.post("/profile/upload-resume")
async def upload_resume(file: UploadFile = File(...)) -> dict:
    """Upload a PDF/DOCX resume and auto-parse it into user profile."""
    if not os.environ.get("GEMINI_API_KEY"):
        raise HTTPException(400, "GEMINI_API_KEY not configured.")
    RESUMES_DIR.mkdir(parents=True, exist_ok=True)
    file_path = RESUMES_DIR / (file.filename or "resume.pdf")
    content = await file.read()
    file_path.write_bytes(content)
    logger.info("Uploaded resume: %s (%d bytes)", file_path.name, len(content))
    try:
        parser = ResumeParser()
        profile_data = parser.parse_file(file_path)
        logger.info("Parsed resume file — keys: %s", list(profile_data.keys()))
        # Save parsed profile
        PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        PROFILE_PATH.write_text(json.dumps(profile_data, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"parsed": True, "profile": profile_data}
    except Exception as e:
        logger.exception("Error parsing uploaded resume: %s", e)
        raise HTTPException(500, detail=str(e))

@router.post("/profile/parse-resume")
def parse_resume_text(data: dict) -> dict:
    """Parse resume from text and return profile data."""
    if not os.environ.get("GEMINI_API_KEY"):
        raise HTTPException(400, "GEMINI_API_KEY not configured.")
    text = data.get("text", "")
    if not text.strip():
        raise HTTPException(400, detail="No text provided.")
    logger.info("Parsing resume text (%d chars)", len(text))
    try:
        parser = ResumeParser()
        profile_data = parser.parse_text(text)
        logger.info("Parsed resume text — keys: %s", list(profile_data.keys()))
        return {"parsed": True, "profile": profile_data}
    except Exception as e:
        logger.exception("Error parsing resume text: %s", e)
        raise HTTPException(500, detail=str(e))


# ── GitHub 技术栈同步（SPEC 附录 F.7 TASK-B03） ────────────────────────────────
# sync_profile() 全量跑一个账号大概 5-6 分钟（B02 实测），走同步请求会超时，
# 所以复用 routers/scrapers.py 已有的"后台线程 + 轮询"模式，不新起一套。


class GitHubSyncRequest(BaseModel):
    username: str | None = None
    exclude_forks: bool = True


def _run_github_sync(task_id: str, username: str | None, exclude_forks: bool) -> None:
    _github_sync_tasks[task_id].update(status="running", progress="Scanning GitHub repositories...")
    try:
        inferred = asyncio.run(sync_profile(username=username, exclude_forks=exclude_forks))
        try:
            existing = UserProfile.load()
            existing_skills = existing.skills
        except FileNotFoundError:
            existing_skills = []

        diff = build_skill_diff(existing_skills, inferred)
        _github_sync_tasks[task_id].update(
            status="done",
            progress=f"Found {len(diff)} proposed change(s).",
            diff=[d.model_dump() for d in diff],
        )
    except Exception as e:
        logger.exception("GitHub profile sync failed: %s", e)
        _github_sync_tasks[task_id].update(status="error", progress=str(e), error=str(e))


@router.post("/profile/github-sync")
def start_github_sync(req: GitHubSyncRequest) -> dict:
    if not os.environ.get("GITHUB_TOKEN"):
        raise HTTPException(400, detail="GITHUB_TOKEN not configured.")
    task_id = str(uuid.uuid4())
    _github_sync_tasks[task_id] = {"status": "pending", "progress": "Queued"}
    threading.Thread(
        target=_run_github_sync, args=(task_id, req.username, req.exclude_forks), daemon=True
    ).start()
    return {"task_id": task_id}


@router.get("/profile/github-sync/tasks/{task_id}")
def get_github_sync_task(task_id: str) -> dict:
    if task_id not in _github_sync_tasks:
        raise HTTPException(404, "Task not found")
    return _github_sync_tasks[task_id]


class ApplyGitHubSyncRequest(BaseModel):
    task_id: str
    accepted_skill_names: list[str]


@router.post("/profile/github-sync/apply")
def apply_github_sync(req: ApplyGitHubSyncRequest) -> dict:
    """只合并人工勾选接受的 diff 条目——严禁自动覆盖 UserProfile（SPEC 约束），
    拒绝/未勾选的条目原样跳过，不写入。合并规则见 profile_sync.apply_skill_diff
    的 docstring（跟 Resume.tsx::mergeSkills 同一套规则，不是另起一套）。
    """
    task = _github_sync_tasks.get(req.task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    if task.get("status") != "done":
        raise HTTPException(400, detail=f"Task is not ready (status={task.get('status')}).")

    from backend.app.agents.profile_sync import SkillDiffEntry

    diff_entries = [SkillDiffEntry(**d) for d in task.get("diff", [])]

    try:
        existing = UserProfile.load()
    except FileNotFoundError:
        raise HTTPException(400, detail="User profile not found. Upload your resume on the Profile page first.")

    merged_skills = apply_skill_diff(existing.skills, diff_entries, set(req.accepted_skill_names))
    updated = existing.model_copy(update={"skills": merged_skills})

    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(json.dumps(updated.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")

    return {"saved": True, "profile": updated.model_dump()}
