"""Profile router — manage user profile JSON."""
import json
import logging
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from backend.app.agents.parser import ResumeParser
from backend.app.models.user_profile import UserProfile
from backend.app.config import PROFILE_PATH, RESUMES_DIR

logger = logging.getLogger(__name__)
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
    logger.info("Uploaded resume: %s (%d bytes)", file_path.name, len(content))
    try:
        parser = ResumeParser()
        profile_data = parser.parse_file(file_path)
        logger.info("Parsed resume file — keys: %s", list(profile_data.keys()))
        # Save parsed profile
        PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        PROFILE_PATH.write_text(json.dumps(profile_data, indent=2, ensure_ascii=False), encoding="utf-8")
        # Generate base Word resume (non-fatal)
        try:
            from backend.app.docx_generator import generate_base_resume
            from backend.app.models.user_profile import UserProfile
            profile = UserProfile.model_validate(profile_data)
            generate_base_resume(profile)
        except Exception as e:
            logger.warning("Base resume generation failed: %s", e)
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
