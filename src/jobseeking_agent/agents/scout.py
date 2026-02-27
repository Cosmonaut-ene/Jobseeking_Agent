"""
Scout Agent — 接收粘贴的 JD 文本，解析结构化字段，打分，存库。
"""

import json
import os

from google import genai
from google.genai import types

from jobseeking_agent.db import get_session
from jobseeking_agent.models.job import Job
from jobseeking_agent.models.user_profile import UserProfile

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
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def run(
        self,
        raw_jd: str,
        user_profile: UserProfile,
        source: str = "manual",
        source_url: str = "",
        # Scrapers may supply pre-extracted fields to skip a parse LLM call
        title: str = "",
        company: str = "",
        location: str = "",
        salary_range: str = "",
    ) -> Job:
        # Only call parse if scrapers didn't already supply title/company
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

        job = Job(
            source=source,
            source_url=source_url,
            raw_jd=raw_jd,
            title=parsed.get("title", ""),
            company=parsed.get("company", ""),
            location=parsed.get("location", ""),
            salary_range=parsed.get("salary_range", ""),
            skills_required=parsed.get("skills_required", []),
            match_score=gap.get("match_score", 0.0),
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
