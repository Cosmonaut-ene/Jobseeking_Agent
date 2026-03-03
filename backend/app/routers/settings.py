"""Settings router."""
import os
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["settings"])

_SETTINGS_FILE = Path("data/settings.json")


def _load_settings() -> dict:
    if _SETTINGS_FILE.exists():
        import json
        return json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
    return {}


def _save_settings(data: dict) -> None:
    import json
    _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


@router.get("/settings")
def get_settings() -> dict:
    s = _load_settings()
    # Don't expose actual API key value, just whether it's set
    return {
        "gemini_api_key_set": bool(os.environ.get("GEMINI_API_KEY")),
        "notification_webhook_set": bool(os.environ.get("NOTIFICATION_WEBHOOK_URL")),
        "scheduler_enabled": os.environ.get("SCHEDULER_ENABLED", "true").lower() == "true",
        "scheduler_hour": int(os.environ.get("SCHEDULER_HOUR", "9")),
        "scheduler_minute": int(os.environ.get("SCHEDULER_MINUTE", "0")),
        "high_score_threshold": float(os.environ.get("HIGH_SCORE_THRESHOLD", "0.80")),
        "mid_score_threshold": float(os.environ.get("MID_SCORE_THRESHOLD", "0.70")),
        **s,
    }


class SettingsUpdate(BaseModel):
    gemini_api_key: str | None = None
    notification_webhook_url: str | None = None
    notification_chat_id: str | None = None
    scheduler_enabled: bool | None = None
    scheduler_hour: int | None = None
    scheduler_minute: int | None = None
    high_score_threshold: float | None = None
    mid_score_threshold: float | None = None
    scraper_config: dict | None = None


@router.post("/settings")
def update_settings(body: SettingsUpdate) -> dict:
    env_path = Path(".env")
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text().splitlines()

    def _set_env(key: str, value: str) -> None:
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}"
                return
        lines.append(f"{key}={value}")

    if body.gemini_api_key is not None:
        os.environ["GEMINI_API_KEY"] = body.gemini_api_key
        _set_env("GEMINI_API_KEY", body.gemini_api_key)
    if body.notification_webhook_url is not None:
        os.environ["NOTIFICATION_WEBHOOK_URL"] = body.notification_webhook_url
        _set_env("NOTIFICATION_WEBHOOK_URL", body.notification_webhook_url)
    if body.notification_chat_id is not None:
        os.environ["NOTIFICATION_CHAT_ID"] = body.notification_chat_id
        _set_env("NOTIFICATION_CHAT_ID", body.notification_chat_id)
    if body.scheduler_enabled is not None:
        val = "true" if body.scheduler_enabled else "false"
        os.environ["SCHEDULER_ENABLED"] = val
        _set_env("SCHEDULER_ENABLED", val)
    if body.scheduler_hour is not None:
        os.environ["SCHEDULER_HOUR"] = str(body.scheduler_hour)
        _set_env("SCHEDULER_HOUR", str(body.scheduler_hour))
    if body.high_score_threshold is not None:
        os.environ["HIGH_SCORE_THRESHOLD"] = str(body.high_score_threshold)
        _set_env("HIGH_SCORE_THRESHOLD", str(body.high_score_threshold))
    if body.mid_score_threshold is not None:
        os.environ["MID_SCORE_THRESHOLD"] = str(body.mid_score_threshold)
        _set_env("MID_SCORE_THRESHOLD", str(body.mid_score_threshold))

    env_path.write_text("\n".join(lines) + "\n")

    # Save scraper config separately
    if body.scraper_config is not None:
        _save_settings({"scraper_config": body.scraper_config})

    return {"saved": True}
