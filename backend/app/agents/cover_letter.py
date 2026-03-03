"""Cover Letter generator — extracted from ApplierAgent."""
import json
import os
from pathlib import Path
from google import genai
from google.genai import types
from backend.app.models.job import Job
from backend.app.models.resume_version import ResumeVersion
from backend.app.models.user_profile import UserProfile
from backend.app.config import COVER_LETTERS_DIR

MODEL = "gemini-2.5-flash"

COVER_LETTER_SYSTEM = """You are an expert career coach writing a cover letter.
RULES:
1. Only reference facts, projects, and skills present in the candidate profile — no fabrication.
2. Structure: opening → body (2 strongest relevant projects/achievements) → closing.
3. Tone: confident, specific, not generic. Avoid clichés.
4. Length: 3 short paragraphs, under 250 words total.
5. Address to "Hiring Manager" unless a contact name is provided."""

COVER_LETTER_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "subject_line": types.Schema(type=types.Type.STRING),
        "body": types.Schema(type=types.Type.STRING),
    },
    required=["subject_line", "body"],
)


class CoverLetterAgent:
    def __init__(self) -> None:
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))

    def generate(self, job: Job, resume_version: ResumeVersion, user_profile: UserProfile) -> tuple[str, str]:
        """Returns (subject_line, body)."""
        content = resume_version.content_json
        projects_text = "\n".join(
            f"- {p['name']}: " + "; ".join(b["rewritten"] for b in p.get("bullets", []))
            for p in content.get("projects", [])
        )
        prompt = (
            f"## Candidate\nName: {user_profile.name}\n\n"
            f"## Tailored Summary\n{content.get('summary', '')}\n\n"
            f"## Key Projects\n{projects_text}\n\n"
            f"## Target Role\n{job.title} at {job.company}\n\n"
            f"## Job Description (excerpt)\n{job.raw_jd[:2000]}\n\n"
            "Write a cover letter for this application."
        )
        response = self.client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=COVER_LETTER_SYSTEM,
                response_mime_type="application/json",
                response_schema=COVER_LETTER_SCHEMA,
            ),
        )
        result = json.loads(response.text)
        return result["subject_line"], result["body"]

    def save(self, job: Job, subject_line: str, body: str) -> str:
        """Save cover letter to file, return path."""
        COVER_LETTERS_DIR.mkdir(parents=True, exist_ok=True)
        safe_company = "".join(c if c.isalnum() else "_" for c in job.company)
        safe_title = "".join(c if c.isalnum() else "_" for c in job.title)
        filename = f"{safe_company}_{safe_title}_{job.id[:8]}.txt"
        path = COVER_LETTERS_DIR / filename
        path.write_text(f"Subject: {subject_line}\n\n{body}", encoding="utf-8")
        return str(path)
