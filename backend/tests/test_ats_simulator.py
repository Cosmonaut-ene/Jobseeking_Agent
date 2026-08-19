"""Tests for the composite ATS simulator (SPEC 附录 F.5 TASK-C03)."""
from backend.app.ats.simulator import DIAGNOSIS_DIFF_THRESHOLD, simulate_ats
from backend.app.models.user_profile import Education, Experience, Preferences, Skill, UserProfile


def _make_profile() -> UserProfile:
    return UserProfile(
        name="Jane Doe",
        target_roles=["Software Engineer"],
        skills=[Skill(name="Kubernetes", level="intermediate", years=2.0)],
        experience=[Experience(company="Acme Corp", role="Engineer", duration="2022-2024")],
        projects=[],
        education=[Education(institution="Test University", degree="BSc")],
        preferences=Preferences(),
    )


def _make_resume(tmp_path, text: str):
    path = tmp_path / "resume.docx"
    from docx import Document

    doc = Document()
    doc.add_paragraph(text)
    doc.save(path)
    return path


def test_deterministic_score_is_reproducible(tmp_path):
    resume_file = _make_resume(tmp_path, "Jane Doe — Kubernetes — Acme Corp — Test University")
    profile = _make_profile()
    kwargs = dict(
        resume_file_path=resume_file,
        profile=profile,
        jd_text="Looking for a Kubernetes engineer",
        ats_keywords=["Kubernetes", "Docker"],
        resume_text="Experienced with Kubernetes and Docker deployments",
        llm_ats_pct=80.0,
    )
    reports = [simulate_ats(**kwargs) for _ in range(5)]
    assert len({r.deterministic_ats_score for r in reports}) == 1
    assert len({tuple(r.diagnosis) for r in reports}) == 1


def test_no_diagnosis_when_scores_agree(tmp_path):
    resume_file = _make_resume(tmp_path, "Jane Doe — Kubernetes — Acme Corp — Test University")
    llm_ats_pct = 100.0  # matches the expected high deterministic score -> no diagnosis
    report = simulate_ats(
        resume_file_path=resume_file,
        profile=_make_profile(),
        jd_text="",
        ats_keywords=["Kubernetes"],
        resume_text="Kubernetes expert",
        llm_ats_pct=llm_ats_pct,
    )
    assert abs(report.deterministic_ats_score - llm_ats_pct) <= DIAGNOSIS_DIFF_THRESHOLD
    assert report.diagnosis == []


def test_diagnosis_triggered_when_scores_diverge_and_is_actionable(tmp_path):
    resume_file = _make_resume(tmp_path, "Jane Doe — Kubernetes — Acme Corp — Test University")
    report = simulate_ats(
        resume_file_path=resume_file,
        profile=_make_profile(),
        jd_text="",
        ats_keywords=["Rust", "GraphQL", "Terraform"],  # none present in resume_text below
        resume_text="Generic experience with no matching keywords at all",
        llm_ats_pct=95.0,  # LLM thinks it's great; deterministic keyword score will be 0
    )
    assert report.diagnosis != []
    # must be specific/actionable, not a generic "score is low" placeholder
    assert any("覆盖率" in d or "解析" in d for d in report.diagnosis)


def test_no_diagnosis_when_llm_score_not_provided(tmp_path):
    resume_file = _make_resume(tmp_path, "Jane Doe")
    report = simulate_ats(
        resume_file_path=resume_file,
        profile=_make_profile(),
        jd_text="",
        ats_keywords=["Rust"],
        resume_text="no match here",
        llm_ats_pct=None,
    )
    assert report.diagnosis == []
