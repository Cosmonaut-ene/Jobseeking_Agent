"""Scout Agent — parse JD, score match, auto-filter by threshold."""
import json
import logging
import os
from google import genai
from google.genai import types
from sqlmodel import Session
from backend.app.database import get_session
from backend.app.models.job import Job
from backend.app.models.user_profile import UserProfile
from backend.app import notifications
from backend.app.config import HIGH_SCORE_THRESHOLD, MID_SCORE_THRESHOLD

logger = logging.getLogger(__name__)
MODEL = "gemini-2.5-flash"

PARSE_SYSTEM = """You are a structured data extractor for job descriptions.
Extract the fields below. If a field is not found, use an empty string or empty list."""

SCORE_SYSTEM = """You are a career advisor evaluating how well a candidate matches a job.
- match_score: float 0.0–1.0
- strong_matches: max 5 short phrases (under 6 words each)
- missing_skills: max 5 skill names (under 4 words each)
- notes: one sentence under 20 words"""

PARSE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "title":           types.Schema(type=types.Type.STRING),
        "company":         types.Schema(type=types.Type.STRING),
        "location":        types.Schema(type=types.Type.STRING),
        "salary_range":    types.Schema(type=types.Type.STRING),
        "skills_required": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(type=types.Type.STRING),
        ),
    },
    required=["title", "company", "location", "salary_range", "skills_required"],
)

SCORE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "match_score":    types.Schema(type=types.Type.NUMBER),
        "strong_matches": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(type=types.Type.STRING),
        ),
        "missing_skills": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(type=types.Type.STRING),
        ),
        "notes": types.Schema(type=types.Type.STRING),
    },
    required=["match_score", "strong_matches", "missing_skills", "notes"],
)


class ScoutAgent:
    def __init__(self) -> None:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        self.client = genai.Client(api_key=api_key)

    def run(
        self,
        raw_jd: str,
        user_profile: UserProfile,
        source: str = "manual",
        source_url: str = "",
        title: str = "",
        company: str = "",
        location: str = "",
        salary_range: str = "",
        auto_filter: bool = True,  # NEW: if True, discard jobs below threshold
        notify: bool = True,       # NEW: if True, push high-score jobs immediately
    ) -> Job | None:
        """
        Returns Job if score >= MID_SCORE_THRESHOLD, else None (auto-discarded).
        High-score jobs (>= HIGH_SCORE_THRESHOLD) trigger immediate notification.
        """
        if title and company:
            parsed = {
                "title": title,
                "company": company,
                "location": location,
                "salary_range": salary_range,
                "skills_required": self._parse_jd(raw_jd).get("skills_required", []),
            }
        else:
            parsed = self._parse_jd(raw_jd)

        gap = self._score(raw_jd, user_profile)
        score = gap.get("match_score", 0.0)

        # Auto-filter: discard below mid threshold
        if auto_filter and score < MID_SCORE_THRESHOLD:
            logger.info(
                "[Scout] Discarded %s @ %s (score=%.2f < %.2f)",
                parsed.get("title", "?"),
                parsed.get("company", "?"),
                score,
                MID_SCORE_THRESHOLD,
            )
            return None

        job = Job(
            source=source,
            source_url=source_url,
            raw_jd=raw_jd,
            title=parsed.get("title", ""),
            company=parsed.get("company", ""),
            location=parsed.get("location", ""),
            salary_range=parsed.get("salary_range", ""),
            skills_required=parsed.get("skills_required", []),
            match_score=score,
            gap_analysis={
                "strong_matches": gap.get("strong_matches", []),
                "missing_skills": gap.get("missing_skills", []),
                "notes": gap.get("notes", ""),
            },
        )

        with get_session() as session:
            session.add(job)
            session.commit()
            session.refresh(job)

        # Immediate push for high-score jobs
        if notify and score >= HIGH_SCORE_THRESHOLD:
            sent = notifications.push_high_score_job(job)
            if sent:
                with get_session() as session:
                    db_job = session.get(Job, job.id)
                    if db_job:
                        db_job.notification_sent = True
                        session.add(db_job)
                        session.commit()
            logger.info("[Scout] High-score job saved + pushed: %s @ %s (%.0f%%)", job.title, job.company, score * 100)
        else:
            logger.info("[Scout] Mid-score job saved: %s @ %s (%.0f%%)", job.title, job.company, score * 100)

        return job

    def _call(self, system: str, user: str, schema: types.Schema) -> dict:
        response = self.client.models.generate_content(
            model=MODEL,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
        return json.loads(response.text)

    def _parse_jd(self, raw_jd: str) -> dict:
        return self._call(
            PARSE_SYSTEM,
            f"Extract structured data from this job description:\n\n{raw_jd}",
            PARSE_SCHEMA,
        )

    def _score(self, raw_jd: str, user_profile: UserProfile) -> dict:
        profile_text = user_profile.to_prompt_text()
        return self._call(
            SCORE_SYSTEM,
            f"## Candidate Profile\n{profile_text}\n\n## Job Description\n{raw_jd}\n\nEvaluate the match.",
            SCORE_SCHEMA,
        )
