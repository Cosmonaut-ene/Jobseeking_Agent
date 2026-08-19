"""Tests for the deterministic literal keyword matching engine (SPEC 附录 F.5 TASK-C02)."""
from backend.app.ats.keyword_match import match_keywords


def test_exact_keyword_hit():
    report = match_keywords(
        jd_text="Looking for a Python engineer",
        resume_text="I have 5 years of experience with Python and FastAPI",
        keywords=["Python"],
    )
    assert report.hits == ["Python"]
    assert report.misses == []
    assert report.alias_hits == []
    assert report.score == 100.0


def test_alias_hit_kubernetes_vs_k8s():
    """JD says Kubernetes, resume abbreviates to K8s — must count as a hit."""
    report = match_keywords(
        jd_text="Kubernetes experience required",
        resume_text="Deployed services on K8s clusters",
        keywords=["Kubernetes"],
    )
    assert report.hits == ["Kubernetes"]
    assert report.misses == []
    assert report.alias_hits == [("Kubernetes", "k8s")]
    assert report.score == 100.0


def test_alias_hit_reverse_direction():
    """JD keyword given as the abbreviation, resume spells it out — still a hit."""
    report = match_keywords(
        jd_text="K8s required",
        resume_text="Extensive Kubernetes deployment experience",
        keywords=["K8s"],
    )
    assert report.hits == ["K8s"]
    assert report.alias_hits == [("K8s", "kubernetes")]


def test_word_boundary_prevents_false_positive():
    """Java must NOT be counted as matched just because JavaScript appears."""
    report = match_keywords(
        jd_text="Java backend developer",
        resume_text="Frontend engineer skilled in JavaScript and React",
        keywords=["Java"],
    )
    assert report.hits == []
    assert report.misses == ["Java"]
    assert report.score == 0.0


def test_empty_keyword_list_scores_100_with_no_hits_or_misses():
    report = match_keywords(jd_text="", resume_text="anything", keywords=[])
    assert report.score == 100.0
    assert report.hits == []
    assert report.misses == []


def test_blank_keywords_in_list_are_skipped_not_counted_as_misses():
    report = match_keywords(jd_text="", resume_text="Python developer", keywords=["Python", "", "   "])
    assert report.hits == ["Python"]
    assert report.misses == []
    assert report.score == 100.0


def test_mixed_hits_and_misses_score_calculation():
    report = match_keywords(
        jd_text="",
        resume_text="Experienced with Python and Docker",
        keywords=["Python", "Docker", "Rust", "Kubernetes"],
    )
    assert set(report.hits) == {"Python", "Docker"}
    assert set(report.misses) == {"Rust", "Kubernetes"}
    assert report.score == 50.0


def test_case_insensitive_matching():
    report = match_keywords(jd_text="", resume_text="skilled in PYTHON programming", keywords=["python"])
    assert report.hits == ["python"]


def test_deterministic_across_repeated_calls():
    args = ("JD text", "Python, Kubernetes, Docker experience", ["Python", "K8s", "Rust"])
    reports = [match_keywords(*args) for _ in range(10)]
    assert len({r.score for r in reports}) == 1
    assert len({tuple(r.hits) for r in reports}) == 1
    assert len({tuple(r.misses) for r in reports}) == 1
