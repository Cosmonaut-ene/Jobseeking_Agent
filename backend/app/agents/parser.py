"""Resume parser — extract UserProfile fields from uploaded PDF/DOCX."""
import json
import os
from pathlib import Path
from google import genai
from google.genai import types

MODEL = "gemini-2.5-flash"

PARSE_SYSTEM = """Extract structured information from this resume text.
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
                    "level": types.Schema(type=types.Type.STRING),
                    "years": types.Schema(type=types.Type.NUMBER),
                },
                required=["name", "level"],
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
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            text = self._extract_pdf(file_path)
        elif suffix in (".docx", ".doc"):
            text = self._extract_docx(file_path)
        else:
            text = file_path.read_text(encoding="utf-8")
        return self.parse_text(text)

    def _extract_pdf(self, path: Path) -> str:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    def _extract_docx(self, path: Path) -> str:
        from docx import Document
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)
