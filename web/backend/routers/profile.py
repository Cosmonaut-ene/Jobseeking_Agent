import json
import os
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from jobseeking_agent.agents.resume_parser import ResumeParserAgent
from jobseeking_agent.models.user_profile import UserProfile

router = APIRouter(tags=["profile"])

PROFILE_PATH = Path("data/user_profile.json")


def _require_api_key() -> None:
    if not os.environ.get("GEMINI_API_KEY"):
        raise HTTPException(
            400,
            detail="GEMINI_API_KEY not configured. Go to Settings to add your API key.",
        )


@router.get("/profile")
def get_profile() -> dict:
    if not PROFILE_PATH.exists():
        raise HTTPException(404, "Profile not found. Upload a resume or create one in the Profile page.")
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


@router.put("/profile")
def update_profile(profile: dict) -> dict:
    try:
        validated = UserProfile.model_validate(profile)
    except Exception as e:
        raise HTTPException(422, detail=str(e))
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(validated.model_dump_json(indent=2), encoding="utf-8")
    return jsonable_encoder(validated)


class ParseTextRequest(BaseModel):
    text: str


@router.post("/profile/parse")
def parse_resume_text(req: ParseTextRequest) -> dict:
    """Parse raw resume text → UserProfile (no file required)."""
    _require_api_key()
    try:
        agent = ResumeParserAgent()
        profile = agent.parse_text(req.text)
        return jsonable_encoder(profile)
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.post("/profile/upload")
async def upload_resume(file: UploadFile) -> dict:
    """Upload PDF/DOCX/TXT resume → parsed UserProfile."""
    _require_api_key()
    suffix = Path(file.filename).suffix.lower() if file.filename else ".txt"
    if suffix not in (".pdf", ".docx", ".doc", ".txt", ".md"):
        raise HTTPException(400, detail=f"Unsupported file type: {suffix}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        agent = ResumeParserAgent()
        profile = agent.parse_file(tmp_path)
        return jsonable_encoder(profile)
    except Exception as e:
        raise HTTPException(500, detail=str(e))
    finally:
        tmp_path.unlink(missing_ok=True)
