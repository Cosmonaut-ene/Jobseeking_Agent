"""Notifications router."""
import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from backend.app import notifications

router = APIRouter(tags=["notifications"])

_tasks: dict[str, dict[str, Any]] = {}


@router.post("/notifications/test")
def test_notification() -> dict:
    sent = notifications._send("🔔 <b>Jobseeking Agent</b> — 通知测试成功！")
    if not sent:
        raise HTTPException(400, "Notification failed — check webhook URL in Settings.")
    return {"sent": True}


@router.post("/notifications/trigger-scout")
def trigger_scout() -> dict:
    task_id = str(uuid.uuid4())
    _tasks[task_id] = {"status": "running", "progress": "Starting..."}

    def _run():
        try:
            from backend.app.scrapers.scheduler import run_daily_scout
            settings_file = Path("data/settings.json")
            settings: dict = {}
            if settings_file.exists():
                settings = json.loads(settings_file.read_text()).get("scraper_config", {})
            result = run_daily_scout(settings)
            if "error" in result:
                _tasks[task_id].update(status="error", progress=result["error"], error=result["error"])
            else:
                _tasks[task_id].update(status="done", progress="Complete", result=result)
        except Exception as e:
            _tasks[task_id].update(status="error", progress=str(e), error=str(e))

    threading.Thread(target=_run, daemon=True).start()
    return {"task_id": task_id}


@router.get("/notifications/tasks/{task_id}")
def get_task(task_id: str) -> dict:
    if task_id not in _tasks:
        raise HTTPException(404, "Task not found")
    return _tasks[task_id]


