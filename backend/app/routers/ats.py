"""ATS simulation router — SPEC 附录 F.5 TASK-C03."""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from backend.app.ats.simulator import simulate_ats
from backend.app.config import RESUMES_DIR
from backend.app.database import engine
from backend.app.models.job import Job
from backend.app.models.resume_version import ResumeVersion
from backend.app.models.user_profile import UserProfile

router = APIRouter(tags=["ats"])

# 系统生成文件不算"用户上传的简历"（F-CONF-01），寻找最新上传件时排除
_GENERATED_FILE_PREFIXES = ("tailored_", "base_resume")


def _find_latest_uploaded_resume() -> Path | None:
    if not RESUMES_DIR.exists():
        return None
    candidates = [
        p for p in RESUMES_DIR.iterdir()
        if p.is_file() and not p.name.startswith(_GENERATED_FILE_PREFIXES)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _flatten_resume_text(content_json: dict) -> str:
    """把 ResumeVersion.content_json 拍平成纯文本，供关键词匹配使用。"""
    parts: list[str] = [content_json.get("summary", "")]
    parts.append(", ".join(content_json.get("skills", [])))
    for proj in content_json.get("projects", []):
        parts.append(proj.get("name", ""))
        for bullet in proj.get("bullets", []):
            text = bullet.get("rewritten", "") if isinstance(bullet, dict) else str(bullet)
            parts.append(text)
    for exp in content_json.get("experience", []):
        parts.append(f"{exp.get('role', '')} {exp.get('company', '')}")
        for bullet in exp.get("bullets", []):
            parts.append(bullet if isinstance(bullet, str) else str(bullet))
    return "\n".join(p for p in parts if p)


class SimulateRequest(BaseModel):
    resume_version_id: str


@router.post("/ats/simulate")
def simulate(req: SimulateRequest) -> dict:
    with Session(engine) as session:
        resume_version = session.get(ResumeVersion, req.resume_version_id)
        if not resume_version:
            raise HTTPException(404, detail="Resume version not found")

        job = session.get(Job, resume_version.job_id)
        if not job:
            raise HTTPException(404, detail="Associated job not found")

        resume_file = _find_latest_uploaded_resume()
        if resume_file is None:
            raise HTTPException(
                400,
                detail="No uploaded resume file found. Upload your resume on the Profile page first.",
            )

        try:
            profile = UserProfile.load()
        except FileNotFoundError:
            raise HTTPException(400, detail="User profile not found.")

        ats_keywords = (job.gap_analysis or {}).get("resume_improvements", {}).get("ats_keywords", [])
        resume_text = _flatten_resume_text(resume_version.content_json or {})
        llm_ats_pct = job.match_score * 100 if job.match_score else None

        report = simulate_ats(
            resume_file_path=resume_file,
            profile=profile,
            jd_text=job.raw_jd,
            ats_keywords=ats_keywords,
            resume_text=resume_text,
            llm_ats_pct=llm_ats_pct,
        )

        resume_version.deterministic_ats_score = report.deterministic_ats_score
        resume_version.ats_report = report.model_dump()
        session.add(resume_version)
        session.commit()

        return report.model_dump()
