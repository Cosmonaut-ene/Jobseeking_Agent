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

EVAL_SYSTEM = """You are a senior career advisor and resume coach providing a detailed, actionable evaluation of how well a candidate matches a job description.

Produce a 5-section structured evaluation:

1. MATCH ANALYSIS
   - ats_pct: integer 0–100 representing ATS keyword match percentage
   - strong_matches: up to 6 specific skills/experiences the candidate clearly has (be concrete, e.g. "3 years Python experience", "React + TypeScript projects")
   - missing_skills: up to 6 required skills/qualifications the candidate lacks (be specific, e.g. "AWS certification", "5+ years Java")
   - unmet_requirements: up to 4 hard requirements not met (e.g. "degree in CS required", "must have worked at 200+ person company")
   - notes: 1–2 sentences summarising overall fit

2. SKILLS & QUALIFICATION IMPROVEMENTS
   - technical: up to 5 technical skills to learn/demonstrate (with context why each matters for this role)
   - certifications: up to 3 certifications that would boost this application
   - soft_skills: up to 3 soft skills to highlight or develop
   - tools: up to 4 tools/platforms to add to resume if familiar

3. RESUME CONTENT IMPROVEMENTS
   - bullet_strength: up to 5 specific tips to strengthen existing resume bullets (e.g. "Add a quantified outcome to your ML pipeline bullet")
   - achievements_feedback: 1–2 sentences assessing how well the resume showcases impact vs duties
   - metrics_suggestions: up to 4 suggestions for adding metrics/numbers (e.g. "Quantify how many users your API served")
   - ats_keywords: up to 8 exact keywords from the JD missing from the resume that should be incorporated

4. FLOW, GRAMMAR & FORMATTING
   - tone_clarity: up to 3 observations about tone, clarity, or language issues
   - action_verbs: up to 4 weak verbs used and their stronger alternatives (e.g. "Replace 'helped with' → 'Led'")
   - layout: up to 3 formatting/structure suggestions

5. OVERALL RECOMMENDATIONS
   - top_5: exactly 5 highest-priority actions the candidate should take (ordered by impact)
   - quick_wins: up to 3 changes achievable within 1 hour (e.g. "Add 'Agile' keyword to skills section")
   - deeper_improvements: up to 3 medium-term improvements (1–4 weeks effort)
   - estimated_improvement_pct: integer — estimated ATS score increase if top recommendations are implemented

Be specific and use examples from the candidate's resume and the job description. Write for a non-expert reader."""

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

EVAL_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "ats_pct": types.Schema(type=types.Type.INTEGER),
        "strong_matches": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
        "missing_skills": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
        "unmet_requirements": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
        "notes": types.Schema(type=types.Type.STRING),
        "skills_improvements": types.Schema(
            type=types.Type.OBJECT,
            properties={
                "technical":      types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                "certifications": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                "soft_skills":    types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                "tools":          types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
            },
            required=["technical", "certifications", "soft_skills", "tools"],
        ),
        "resume_improvements": types.Schema(
            type=types.Type.OBJECT,
            properties={
                "bullet_strength":       types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                "achievements_feedback": types.Schema(type=types.Type.STRING),
                "metrics_suggestions":   types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                "ats_keywords":          types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
            },
            required=["bullet_strength", "achievements_feedback", "metrics_suggestions", "ats_keywords"],
        ),
        "formatting_improvements": types.Schema(
            type=types.Type.OBJECT,
            properties={
                "tone_clarity": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                "action_verbs": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                "layout":       types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
            },
            required=["tone_clarity", "action_verbs", "layout"],
        ),
        "recommendations": types.Schema(
            type=types.Type.OBJECT,
            properties={
                "top_5":                    types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                "quick_wins":               types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                "deeper_improvements":      types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                "estimated_improvement_pct": types.Schema(type=types.Type.INTEGER),
            },
            required=["top_5", "quick_wins", "deeper_improvements", "estimated_improvement_pct"],
        ),
    },
    required=["ats_pct", "strong_matches", "missing_skills", "unmet_requirements", "notes",
              "skills_improvements", "resume_improvements", "formatting_improvements", "recommendations"],
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

        gap = self._evaluate(raw_jd, user_profile)
        score = gap.get("ats_pct", 0) / 100

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
                "ats_pct": gap.get("ats_pct", 0),
                "strong_matches": gap.get("strong_matches", []),
                "missing_skills": gap.get("missing_skills", []),
                "unmet_requirements": gap.get("unmet_requirements", []),
                "notes": gap.get("notes", ""),
                "skills_improvements": gap.get("skills_improvements", {}),
                "resume_improvements": gap.get("resume_improvements", {}),
                "formatting_improvements": gap.get("formatting_improvements", {}),
                "recommendations": gap.get("recommendations", {}),
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

    def _evaluate(self, raw_jd: str, user_profile: UserProfile) -> dict:
        profile_text = user_profile.to_prompt_text()
        return self._call(
            EVAL_SYSTEM,
            f"## Candidate Profile\n{profile_text}\n\n## Job Description\n{raw_jd}\n\nProvide the full 5-section evaluation.",
            EVAL_SCHEMA,
        )
