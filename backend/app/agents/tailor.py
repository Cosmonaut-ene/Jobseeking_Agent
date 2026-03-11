"""
Tailor Agent — 根据 JD 定制简历。

约束：
  - LLM 只能改写措辞，不能添加 source bullet 中没有的事实/技术/数字
  - 每个输出 bullet 必须携带 source_raw（原始锚点），供人工 review
"""

import json
import os

from google import genai
from google.genai import types

from backend.app.models.job import Job
from backend.app.models.resume_version import ResumeVersion
from backend.app.models.user_profile import UserProfile

MODEL = "gemini-2.5-flash"

TAILOR_SYSTEM = """You are an expert resume writer helping tailor a candidate's resume for a specific job.

STRICT RULES — violation will cause the resume to be rejected:
1. Each rewritten bullet MUST be derived from its source_raw text.
   Do NOT fabricate new experiences, roles, or accomplishments not in source_raw.
   You MAY incorporate exact JD keywords and terminology from the "Target ATS Keywords"
   section below into existing bullets where contextually appropriate.
2. You MAY: rephrase, reorder clauses, emphasise keywords from the JD, use stronger action verbs.
3. Keep each bullet concise: 1–2 lines, starting with a strong past-tense action verb.
4. summary: 2–3 sentences tailored to the role. Only use facts from the candidate profile.
5. selected_skills: ordered by relevance to the JD, max 12 items.
6. Prioritise weaving "Target ATS Keywords" naturally into bullets.
   Prioritise bullets where "Quantification Opportunities" apply."""

ATS_EVAL_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "ats_pct": types.Schema(type=types.Type.INTEGER),
    },
    required=["ats_pct"],
)

TAILOR_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "summary": types.Schema(type=types.Type.STRING),
        "selected_skills": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(type=types.Type.STRING),
        ),
        "tailored_projects": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "name": types.Schema(type=types.Type.STRING),
                    "bullets": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "rewritten": types.Schema(type=types.Type.STRING),
                                "source_raw": types.Schema(type=types.Type.STRING),
                            },
                            required=["rewritten", "source_raw"],
                        ),
                    ),
                },
                required=["name", "bullets"],
            ),
        ),
        "changes_summary": types.Schema(type=types.Type.STRING),
    },
    required=["summary", "selected_skills", "tailored_projects", "changes_summary"],
)


class TailorAgent:
    def __init__(self) -> None:
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def run(self, job: Job, user_profile: UserProfile) -> ResumeVersion:
        result = self._tailor(job, user_profile)
        ats_score = self._eval_ats_score(result, job.raw_jd) / 100

        content_json = {
            "name": user_profile.name,
            "summary": result["summary"],
            "skills": result["selected_skills"],
            "projects": result["tailored_projects"],
            # experience passed through unchanged (empty for now)
            "experience": [
                {
                    "company": exp.company,
                    "role": exp.role,
                    "duration": exp.duration,
                    "bullets": [b.raw for b in exp.bullets],
                }
                for exp in user_profile.experience
            ],
        }

        return ResumeVersion(
            job_id=job.id,
            content_json=content_json,
            ats_score=ats_score,
            changes_summary=result["changes_summary"],
        )

    def _tailor(self, job: Job, user_profile: UserProfile) -> dict:
        profile_text = user_profile.to_prompt_text()
        resume_improvements = job.gap_analysis.get("resume_improvements", {})
        ats_keywords: list[str] = resume_improvements.get("ats_keywords", [])
        metrics_suggestions: list[str] = resume_improvements.get("metrics_suggestions", [])

        prompt = (
            f"## Job Description\n{job.raw_jd}\n\n"
            f"## Required Skills (from JD)\n{', '.join(job.skills_required)}\n\n"
            f"## Gap Analysis\n"
            f"Strong matches: {', '.join(job.gap_analysis.get('strong_matches', []))}\n"
            f"Missing skills: {', '.join(job.gap_analysis.get('missing_skills', []))}\n\n"
            f"## Target ATS Keywords (incorporate these into bullets where appropriate)\n"
            f"{', '.join(ats_keywords)}\n\n"
            f"## Quantification Opportunities\n"
            f"{chr(10).join('- ' + s for s in metrics_suggestions)}\n\n"
            f"## Candidate Profile\n{profile_text}\n\n"
            "Tailor the resume for this job. Select the most relevant projects and rewrite "
            "their bullets to align with the JD keywords. Follow the strict rules."
        )
        response = self.client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=TAILOR_SYSTEM,
                response_mime_type="application/json",
                response_schema=TAILOR_SCHEMA,
            ),
        )
        return json.loads(response.text)

    def _eval_ats_score(self, result: dict, raw_jd: str) -> int:
        resume_text = "\n".join([
            result.get("summary", ""),
            "Skills: " + ", ".join(result.get("selected_skills", [])),
            "\n".join(
                b["rewritten"]
                for proj in result.get("tailored_projects", [])
                for b in proj.get("bullets", [])
            ),
        ])
        prompt = (
            f"## Tailored Resume\n{resume_text}\n\n"
            f"## Job Description\n{raw_jd}\n\n"
            "Return the ATS keyword match percentage (0–100) of the tailored resume against the job description."
        )
        response = self.client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ATS_EVAL_SCHEMA,
            ),
        )
        return json.loads(response.text).get("ats_pct", 0)
