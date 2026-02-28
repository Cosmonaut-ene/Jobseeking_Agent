"""
ResumeParserAgent — extracts a structured UserProfile from PDF/DOCX/text resumes.
Follows the same _call() pattern as scout.py.
"""

import json
import os
from pathlib import Path

from google import genai
from google.genai import types

from jobseeking_agent.models.user_profile import (
    Bullet,
    Education,
    Experience,
    Preferences,
    Project,
    SalaryRange,
    Skill,
    UserProfile,
)

MODEL = "gemini-2.5-flash"

PARSER_SYSTEM = """You are an expert resume parser. Extract ALL structured information.
RULES:
1. Bullet raw: keep exact achievement text with numbers/metrics verbatim
2. Bullet tech: list tech names mentioned in that bullet
3. Bullet metric: key quantitative metric, else empty string
4. Skill level: expert(5+y / lead/architect), intermediate(2-4y), beginner(<2y)
5. Duration format: "YYYY-MM ~ YYYY-MM" or "YYYY-MM ~ present"
6. target_roles: infer from job titles, summary, or objective section"""

# ── Nested schemas ────────────────────────────────────────────────────────────

BULLET_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "raw":    types.Schema(type=types.Type.STRING),
        "tech":   types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
        "metric": types.Schema(type=types.Type.STRING),
    },
    required=["raw", "tech", "metric"],
)

SKILL_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "name":  types.Schema(type=types.Type.STRING),
        "level": types.Schema(type=types.Type.STRING),
        "years": types.Schema(type=types.Type.NUMBER),
    },
    required=["name", "level", "years"],
)

EXPERIENCE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "company":  types.Schema(type=types.Type.STRING),
        "role":     types.Schema(type=types.Type.STRING),
        "duration": types.Schema(type=types.Type.STRING),
        "bullets":  types.Schema(type=types.Type.ARRAY, items=BULLET_SCHEMA),
    },
    required=["company", "role", "duration", "bullets"],
)

PROJECT_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "name":        types.Schema(type=types.Type.STRING),
        "description": types.Schema(type=types.Type.STRING),
        "tech_stack":  types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
        "bullets":     types.Schema(type=types.Type.ARRAY, items=BULLET_SCHEMA),
    },
    required=["name", "description", "tech_stack", "bullets"],
)

SALARY_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "min":      types.Schema(type=types.Type.INTEGER),
        "max":      types.Schema(type=types.Type.INTEGER),
        "currency": types.Schema(type=types.Type.STRING),
    },
    required=["min", "max", "currency"],
)

EDUCATION_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "institution": types.Schema(type=types.Type.STRING),
        "degree":      types.Schema(type=types.Type.STRING),
        "field":       types.Schema(type=types.Type.STRING),
        "duration":    types.Schema(type=types.Type.STRING),
        "gpa":         types.Schema(type=types.Type.STRING),
    },
    required=["institution", "degree", "field", "duration", "gpa"],
)

PREFERENCES_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "locations":    types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
        "salary_range": SALARY_SCHEMA,
        "job_types":    types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
    },
    required=["locations", "job_types"],
)

PROFILE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "name":         types.Schema(type=types.Type.STRING),
        "target_roles": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
        "skills":       types.Schema(type=types.Type.ARRAY, items=SKILL_SCHEMA),
        "experience":   types.Schema(type=types.Type.ARRAY, items=EXPERIENCE_SCHEMA),
        "projects":     types.Schema(type=types.Type.ARRAY, items=PROJECT_SCHEMA),
        "education":    types.Schema(type=types.Type.ARRAY, items=EDUCATION_SCHEMA),
        "preferences":  PREFERENCES_SCHEMA,
    },
    required=["name", "target_roles", "skills", "experience", "projects", "education", "preferences"],
)


# ── Agent ─────────────────────────────────────────────────────────────────────

class ResumeParserAgent:
    def __init__(self) -> None:
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def parse_file(self, path: Path) -> UserProfile:
        """Dispatch by file extension and return a UserProfile."""
        path = Path(path)
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            text = self._extract_pdf(path)
        elif suffix in (".docx", ".doc"):
            text = self._extract_docx(path)
        elif suffix in (".txt", ".md"):
            text = path.read_text(encoding="utf-8")
        else:
            raise ValueError(f"Unsupported resume format: {suffix!r}")
        return self.parse_text(text)

    def parse_text(self, text: str) -> UserProfile:
        """Parse raw resume text → UserProfile (no file I/O)."""
        raw = self._call(
            PARSER_SYSTEM,
            f"Parse this resume into structured data:\n\n{text}",
            PROFILE_SCHEMA,
        )
        return self._dict_to_profile(raw)

    # ── Extraction helpers ────────────────────────────────────────────────────

    def _extract_pdf(self, path: Path) -> str:
        import pypdf
        reader = pypdf.PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    def _extract_docx(self, path: Path) -> str:
        import docx
        doc = docx.Document(str(path))
        return "\n".join(para.text for para in doc.paragraphs)

    # ── Gemini call (identical to scout._call) ────────────────────────────────

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

    # ── Dict → Pydantic conversion ────────────────────────────────────────────

    def _dict_to_profile(self, data: dict) -> UserProfile:
        prefs_data = data.get("preferences", {})
        salary_data = prefs_data.get("salary_range")
        salary = SalaryRange(**salary_data) if salary_data else None

        preferences = Preferences(
            locations=prefs_data.get("locations", []),
            salary_range=salary,
            job_types=prefs_data.get("job_types", []),
        )

        skills = [Skill(**s) for s in data.get("skills", [])]

        experience = []
        for exp in data.get("experience", []):
            bullets = [Bullet(**b) for b in exp.get("bullets", [])]
            experience.append(Experience(
                company=exp.get("company", ""),
                role=exp.get("role", ""),
                duration=exp.get("duration", ""),
                bullets=bullets,
            ))

        projects = []
        for proj in data.get("projects", []):
            bullets = [Bullet(**b) for b in proj.get("bullets", [])]
            projects.append(Project(
                name=proj.get("name", ""),
                description=proj.get("description", ""),
                tech_stack=proj.get("tech_stack", []),
                bullets=bullets,
            ))

        education = [
            Education(
                institution=e.get("institution", ""),
                degree=e.get("degree", ""),
                field=e.get("field", ""),
                duration=e.get("duration", ""),
                gpa=e.get("gpa", ""),
            )
            for e in data.get("education", [])
        ]

        return UserProfile(
            name=data.get("name", ""),
            target_roles=data.get("target_roles", []),
            skills=skills,
            experience=experience,
            projects=projects,
            education=education,
            preferences=preferences,
        )
