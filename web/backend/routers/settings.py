import os

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["settings"])


@router.get("/settings/status")
def get_status() -> dict:
    """Check whether GEMINI_API_KEY is configured."""
    key = os.environ.get("GEMINI_API_KEY", "")
    return {"has_key": bool(key), "key_preview": f"...{key[-4:]}" if key else ""}


class KeyRequest(BaseModel):
    key: str


@router.post("/settings/key")
def set_key(req: KeyRequest) -> dict:
    """Dynamically inject GEMINI_API_KEY into the current process."""
    os.environ["GEMINI_API_KEY"] = req.key.strip()
    return {"status": "ok"}
