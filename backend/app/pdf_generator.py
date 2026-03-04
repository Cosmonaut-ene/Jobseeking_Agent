"""PDF resume generator using WeasyPrint + Jinja2."""
import logging
from pathlib import Path

from jinja2 import Template
from weasyprint import HTML

logger = logging.getLogger(__name__)


def generate_resume_pdf(
    tailored_content: dict,
    profile,
    template_path: Path | str,
    output_path: Path | str,
) -> str:
    """
    Render tailored resume to PDF.

    tailored_content: dict with keys summary, skills (list[str]), projects, experience
    profile: UserProfile object with .name, .education
    Returns output_path as str.
    """
    template_path = Path(template_path)
    output_path = Path(output_path)

    if not template_path.exists():
        raise FileNotFoundError(f"Resume template not found: {template_path}")

    # Build template context
    context = {
        "name": getattr(profile, "name", ""),
        "summary": tailored_content.get("summary", ""),
        "skills": tailored_content.get("skills")
        or tailored_content.get("selected_skills")
        or [],
        "projects": tailored_content.get("projects")
        or tailored_content.get("tailored_projects")
        or [],
        "experience": tailored_content.get("experience")
        or tailored_content.get("tailored_experience")
        or [],
        "education": getattr(profile, "education", []),
    }

    template_str = template_path.read_text(encoding="utf-8")
    html_str = Template(template_str).render(**context)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html_str).write_pdf(str(output_path))

    logger.info("Generated PDF resume: %s", output_path)
    return str(output_path)
