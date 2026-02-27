"""
Applier Agent — 生成 cover letter，创建 Application 记录。

渠道策略：
  email      → 生成 cover letter + 邮件草稿，保存到 data/cover_letters/
  easy_apply → 生成 cover letter（用于填表），同上保存
  manual     → 仅记录投递，不生成文件
"""

import json
import os
from datetime import date, timedelta
from pathlib import Path

from google import genai
from google.genai import types

from jobseeking_agent.models.application import Application, ApplicationChannel
from jobseeking_agent.models.job import Job
from jobseeking_agent.models.resume_version import ResumeVersion
from jobseeking_agent.models.user_profile import UserProfile

MODEL = "gemini-2.5-flash"
COVER_LETTER_DIR = Path("data/cover_letters")

COVER_LETTER_SYSTEM = """You are an expert career coach writing a cover letter.

RULES:
1. Only reference facts, projects, and skills present in the candidate profile — no fabrication.
2. Structure: opening (why this company/role) → body (2 strongest relevant projects/achievements) → closing (call to action).
3. Tone: confident, specific, not generic. Avoid clichés like "I am a passionate professional".
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


class ApplierAgent:
    def __init__(self) -> None:
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def run(
        self,
        job: Job,
        resume_version: ResumeVersion,
        user_profile: UserProfile,
        channel: ApplicationChannel,
        notes: str = "",
    ) -> tuple[Application, str | None]:
        """
        Returns (Application record, cover_letter_path or None).
        Does NOT commit to DB — caller is responsible.
        """
        cover_letter_path = None

        if channel != ApplicationChannel.manual:
            cover = self._generate_cover_letter(job, resume_version, user_profile)
            cover_letter_path = self._save_cover_letter(job, cover)

        application = Application(
            job_id=job.id,
            resume_version_id=resume_version.id,
            channel=channel,
            follow_up_date=date.today() + timedelta(days=7),
            notes=notes,
        )

        return application, cover_letter_path

    def _generate_cover_letter(
        self, job: Job, resume_version: ResumeVersion, user_profile: UserProfile
    ) -> dict:
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
        return json.loads(response.text)

    def _save_cover_letter(self, job: Job, cover: dict) -> str:
        COVER_LETTER_DIR.mkdir(parents=True, exist_ok=True)
        safe_company = "".join(c if c.isalnum() else "_" for c in job.company)
        safe_title = "".join(c if c.isalnum() else "_" for c in job.title)
        filename = f"{safe_company}_{safe_title}_{job.id[:8]}.txt"
        path = COVER_LETTER_DIR / filename

        content = f"Subject: {cover['subject_line']}\n\n{cover['body']}"
        path.write_text(content, encoding="utf-8")
        return str(path)
