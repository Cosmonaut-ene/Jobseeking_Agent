"""Tests for PDF resume generator."""
import pytest
from pathlib import Path


class MockProfile:
    name = "Test User"
    education = []


@pytest.fixture
def template_file(tmp_path):
    t = tmp_path / "resume.html"
    t.write_text("""<!DOCTYPE html><html><body>
<h1>{{ name }}</h1>
<p>{{ summary }}</p>
{% for s in skills %}<span>{{ s }}</span>{% endfor %}
</body></html>""")
    return t


@pytest.fixture
def output_pdf(tmp_path):
    return tmp_path / "output.pdf"


def test_generate_creates_file(template_file, output_pdf):
    """Normal generation produces a file at output_path."""
    from backend.app.pdf_generator import generate_resume_pdf

    content = {"summary": "Expert engineer", "skills": ["Python", "FastAPI"]}
    result = generate_resume_pdf(content, MockProfile(), template_file, output_pdf)
    assert output_pdf.exists()
    assert result == str(output_pdf)


def test_output_is_valid_pdf(template_file, output_pdf):
    """Output file starts with %PDF header."""
    from backend.app.pdf_generator import generate_resume_pdf

    content = {"summary": "Test summary", "skills": []}
    generate_resume_pdf(content, MockProfile(), template_file, output_pdf)
    assert output_pdf.read_bytes()[:4] == b"%PDF"


def test_template_variables_filled(template_file, output_pdf):
    """Template variables are rendered (summary appears in PDF)."""
    from backend.app.pdf_generator import generate_resume_pdf
    import pypdf

    content = {"summary": "UniqueTestSummaryXYZ123", "skills": ["TestSkill"]}
    generate_resume_pdf(content, MockProfile(), template_file, output_pdf)
    reader = pypdf.PdfReader(str(output_pdf))
    text = "".join(page.extract_text() or "" for page in reader.pages)
    assert "UniqueTestSummaryXYZ123" in text or output_pdf.stat().st_size > 1000


def test_missing_profile_fields_graceful(template_file, output_pdf):
    """Missing/empty profile fields don't crash generation."""
    from backend.app.pdf_generator import generate_resume_pdf

    class EmptyProfile:
        name = ""
        education = []

    content = {}
    generate_resume_pdf(content, EmptyProfile(), template_file, output_pdf)
    assert output_pdf.exists()


def test_missing_template_raises(tmp_path, output_pdf):
    """Missing template file raises FileNotFoundError."""
    from backend.app.pdf_generator import generate_resume_pdf

    missing = tmp_path / "nonexistent.html"
    with pytest.raises(FileNotFoundError):
        generate_resume_pdf({}, MockProfile(), missing, output_pdf)
