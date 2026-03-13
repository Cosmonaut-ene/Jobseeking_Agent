"""Files router — serve generated resume files."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.app.config import RESUMES_DIR

router = APIRouter(tags=["files"])


@router.get("/files/{job_id}/resume.docx")
def download_resume_docx(job_id: str):
    path = RESUMES_DIR / f"tailored_{job_id}.docx"
    if not path.exists():
        raise HTTPException(404, "Word resume not found. Run Tailor first.")
    return FileResponse(
        str(path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"resume_{job_id}.docx",
    )
