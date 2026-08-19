"""Resume parser — extract UserProfile fields from uploaded PDF/DOCX."""
import json
import os
from pathlib import Path
from google import genai
from google.genai import types

MODEL = "gemini-2.5-flash"

PARSE_SYSTEM = """You are a resume parser. Extract structured information from this resume text.

CRITICAL: Only extract what is explicitly present in the text.
- If a field (e.g. name, target_roles) is not found, return an empty string "" or empty array [].
- Do NOT guess, fabricate, or fill in placeholder values like "Unknown", "N/A", "Not provided", etc.
- The input may be a partial snippet (e.g. only one job entry). That is fine — return only what is there.

For each skill, you MUST infer:
- level: one of "beginner", "intermediate", or "expert"
  - "beginner":     < 1 year of use, or briefly mentioned without depth
  - "intermediate": 1-3 years of use, or used across multiple projects
  - "expert":       3+ years, listed as primary strength, or described as advanced/proficient
- years: estimated years of experience as a float (e.g. 2.5).
  Infer from: explicit statements ("5 years of Python"), date ranges in work history
  where the skill was applied, education duration, or project history.
  If the skill appears in one short project, estimate 0.5. Never leave years as 0
  unless the skill was literally just mentioned as a buzzword with no evidence of use.

Return a JSON object matching the UserProfile schema."""

PROFILE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "name": types.Schema(type=types.Type.STRING),
        "target_roles": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
        "skills": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "name": types.Schema(type=types.Type.STRING),
                    "level": types.Schema(
                        type=types.Type.STRING,
                        enum=["beginner", "intermediate", "expert"],
                    ),
                    "years": types.Schema(type=types.Type.NUMBER),
                },
                required=["name", "level", "years"],
            ),
        ),
        "experience": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "company": types.Schema(type=types.Type.STRING),
                    "role": types.Schema(type=types.Type.STRING),
                    "duration": types.Schema(type=types.Type.STRING),
                    "bullets": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "raw": types.Schema(type=types.Type.STRING),
                                "tech": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                                "metric": types.Schema(type=types.Type.STRING),
                            },
                            required=["raw"],
                        ),
                    ),
                },
                required=["company", "role", "duration"],
            ),
        ),
        "projects": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "name": types.Schema(type=types.Type.STRING),
                    "description": types.Schema(type=types.Type.STRING),
                    "tech_stack": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                    "bullets": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "raw": types.Schema(type=types.Type.STRING),
                                "tech": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                                "metric": types.Schema(type=types.Type.STRING),
                            },
                            required=["raw"],
                        ),
                    ),
                },
                required=["name", "description"],
            ),
        ),
        "education": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "institution": types.Schema(type=types.Type.STRING),
                    "degree": types.Schema(type=types.Type.STRING),
                    "field": types.Schema(type=types.Type.STRING),
                    "duration": types.Schema(type=types.Type.STRING),
                    "gpa": types.Schema(type=types.Type.STRING),
                },
                required=["institution", "degree"],
            ),
        ),
        "preferences": types.Schema(
            type=types.Type.OBJECT,
            properties={
                "locations": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                "job_types": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
            },
        ),
    },
    required=["name", "target_roles", "skills", "experience", "projects", "preferences"],
)


class ResumeParser:
    def __init__(self) -> None:
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))

    def parse_text(self, resume_text: str) -> dict:
        """Parse resume text and return profile dict."""
        response = self.client.models.generate_content(
            model=MODEL,
            contents=f"Parse this resume:\n\n{resume_text}",
            config=types.GenerateContentConfig(
                system_instruction=PARSE_SYSTEM,
                response_mime_type="application/json",
                response_schema=PROFILE_SCHEMA,
            ),
        )
        return json.loads(response.text)

    def parse_file(self, file_path: Path) -> dict:
        """Parse a PDF or DOCX resume file."""
        return self.parse_text(extract_text_from_file(file_path))


def extract_pdf_text(path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_docx_text(path: Path) -> str:
    from docx import Document
    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)


def extract_text_from_file(file_path: Path) -> str:
    """Extract raw text from a resume file (PDF/DOCX/DOC/plain text).

    Shared by ResumeParser (feeds the LLM) and the ATS parseability
    checker (compares against it deterministically) — same extraction
    path, so the checker measures exactly what the parser would see.
    """
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_text(file_path)
    if suffix in (".docx", ".doc"):
        return extract_docx_text(file_path)
    return file_path.read_text(encoding="utf-8")
