"""PDF resume generator using LaTeX (pdflatex / MiKTeX)."""
import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import jinja2

logger = logging.getLogger(__name__)

# Templates directory relative to project root
_TEMPLATES_DIR = Path(__file__).parents[3] / "templates"

# LaTeX special-character escaping map
_LATEX_ESCAPE = str.maketrans({
    "&":  r"\&",
    "%":  r"\%",
    "$":  r"\$",
    "#":  r"\#",
    "_":  r"\_",
    "{":  r"\{",
    "}":  r"\}",
    "~":  r"\textasciitilde{}",
    "^":  r"\textasciicircum{}",
    "\\": r"\textbackslash{}",
})


def _esc(text: str) -> str:
    """Escape a plain-text string for safe inclusion in LaTeX source."""
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    return text.translate(_LATEX_ESCAPE)


def _build_jinja_env() -> jinja2.Environment:
    return jinja2.Environment(
        block_start_string=r"\BLOCK{",
        block_end_string="}",
        variable_start_string=r"\VAR{",
        variable_end_string="}",
        comment_start_string=r"\#{",
        comment_end_string="}",
        trim_blocks=True,
        autoescape=False,
        loader=jinja2.FileSystemLoader(str(_TEMPLATES_DIR)),
    )


def generate_resume_pdf(
    tailored_content: dict,
    profile,
    template_path: Path | str,  # kept for API compat — template name extracted from it
    output_path: Path | str,
) -> str:
    """
    Render tailored resume to PDF via pdflatex.

    tailored_content: dict with summary, skills, experience, projects
    profile: UserProfile with .name, .education
    Returns output_path as str.
    Raises RuntimeError on pdflatex failure or if pdflatex is not installed.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pdflatex = shutil.which("pdflatex")
    if not pdflatex:
        raise RuntimeError(
            "pdflatex not found. Install MiKTeX from https://miktex.org/download "
            "and ensure it is added to PATH."
        )

    # --- Build template context ---
    name = _esc(getattr(profile, "name", "") or "Resume")
    summary = _esc(tailored_content.get("summary", ""))

    raw_skills = (
        tailored_content.get("skills")
        or tailored_content.get("selected_skills")
        or []
    )
    skills = [_esc(str(s)) for s in raw_skills]

    raw_experience = (
        tailored_content.get("experience")
        or tailored_content.get("tailored_experience")
        or []
    )
    experience = []
    for exp in raw_experience:
        if isinstance(exp, dict):
            role = exp.get("role", "")
            company = exp.get("company", "")
            duration = exp.get("duration", "")
            raw_bullets = exp.get("bullets", [])
        else:
            role = getattr(exp, "role", "")
            company = getattr(exp, "company", "")
            duration = getattr(exp, "duration", "")
            raw_bullets = getattr(exp, "bullets", [])
        bullets = [
            _esc(b if isinstance(b, str) else (b.get("rewritten") or b.get("raw", "")))
            for b in raw_bullets
            if b
        ]
        experience.append({
            "role": _esc(role),
            "company": _esc(company),
            "duration": _esc(duration),
            "bullets": bullets,
        })

    raw_projects = (
        tailored_content.get("projects")
        or tailored_content.get("tailored_projects")
        or []
    )
    projects = []
    for proj in raw_projects:
        if isinstance(proj, dict):
            pname = proj.get("name", "")
            raw_bullets = proj.get("bullets", [])
        else:
            pname = getattr(proj, "name", "")
            raw_bullets = getattr(proj, "bullets", [])
        bullets = [
            _esc(b if isinstance(b, str) else (b.get("rewritten") or b.get("raw", "")))
            for b in raw_bullets
            if b
        ]
        projects.append({"name": _esc(pname), "bullets": bullets})

    raw_education = getattr(profile, "education", []) or []
    education = []
    for edu in raw_education:
        if isinstance(edu, dict):
            degree = edu.get("degree", "")
            field = edu.get("field", "")
            institution = edu.get("institution", "")
            duration = edu.get("duration", "")
        else:
            degree = getattr(edu, "degree", "")
            field = getattr(edu, "field", "")
            institution = getattr(edu, "institution", "")
            duration = getattr(edu, "duration", "")
        label = f"{degree}{' in ' + field if field else ''}"
        education.append({
            "label": _esc(label),
            "institution": _esc(institution),
            "duration": _esc(duration),
        })

    ctx = {
        "name": name,
        "summary": summary,
        "skills": skills,
        "experience": experience,
        "projects": projects,
        "education": education,
    }

    # --- Render .tex from Jinja2 template ---
    env = _build_jinja_env()
    template = env.get_template("resume.tex.j2")
    tex_source = template.render(**ctx)

    # --- Compile with pdflatex ---
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = Path(tmpdir) / "resume.tex"
        tex_path.write_text(tex_source, encoding="utf-8")
        result = subprocess.run(
            [
                pdflatex,
                "-interaction=nonstopmode",
                "-output-directory", tmpdir,
                str(tex_path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            log_tail = (result.stdout or "") + (result.stderr or "")
            log_tail = log_tail[-3000:]
            raise RuntimeError(f"pdflatex failed (exit {result.returncode}):\n{log_tail}")
        pdf_tmp = Path(tmpdir) / "resume.pdf"
        shutil.copy(pdf_tmp, output_path)

    logger.info("Generated PDF resume via LaTeX: %s", output_path)
    return str(output_path)
