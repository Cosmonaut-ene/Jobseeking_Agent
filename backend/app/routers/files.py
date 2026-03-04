"""Files router — serve generated PDFs."""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.app.config import RESUMES_DIR

router = APIRouter(tags=["files"])


@router.get("/files/{job_id}/resume.pdf")
def download_resume(job_id: str):
    path = RESUMES_DIR / f"tailored_{job_id}.pdf"
    if not path.exists():
        raise HTTPException(404, "PDF not found. Run Tailor first.")
    return FileResponse(
        str(path), media_type="application/pdf", filename=f"resume_{job_id}.pdf"
    )
