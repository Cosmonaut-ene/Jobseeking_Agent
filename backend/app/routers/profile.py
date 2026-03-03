"""Profile router — manage user profile JSON."""
import json
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from backend.app.agents.parser import ResumeParser
from backend.app.models.user_profile import UserProfile
from backend.app.config import PROFILE_PATH, RESUMES_DIR

router = APIRouter(tags=["profile"])


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
    try:
        parser = ResumeParser()
        profile_data = parser.parse_file(file_path)
        # Save parsed profile
        PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        PROFILE_PATH.write_text(json.dumps(profile_data, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"parsed": True, "profile": profile_data}
    except Exception as e:
        raise HTTPException(500, detail=str(e))
