"""Regression test for a real UX-audit bug: the diagnosis that's supposed to
explain a gap between the AI estimate and the deterministic ATS score was
being computed against the wrong AI number.

TailorAgent._score_deterministically() passed job.match_score (the JD-level
match computed *before* tailoring, by ScoutAgent) into simulate_ats()'s
llm_ats_pct — but the resume panel actually displays resume_version.ats_score
(this specific tailored version's own AI self-eval) right next to the
deterministic score. Comparing the wrong pair meant a real 82% vs 57% gap
(25 points) on screen never triggered the diagnosis, because job.match_score
happened to be within threshold of the deterministic score.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.app.models.job import Job
from backend.app.models.resume_version import ResumeVersion
from backend.app.models.user_profile import Preferences, Skill, UserProfile


def _make_job(match_score: float) -> Job:
    return Job(
        source="manual",
        raw_jd="Looking for a Kubernetes engineer",
        title="Engineer",
        company="Acme",
        skills_required=["Kubernetes"],
        match_score=match_score,
        gap_analysis={
            "strong_matches": [], "missing_skills": [],
            "resume_improvements": {"ats_keywords": ["Kubernetes"], "metrics_suggestions": []},
        },
    )


def _make_profile() -> UserProfile:
    return UserProfile(
        name="Jane Doe", target_roles=["Engineer"],
        skills=[Skill(name="Kubernetes", level="intermediate", years=2.0)],
        experience=[], projects=[], preferences=Preferences(),
    )


def test_llm_ats_pct_uses_this_versions_own_ai_score_not_job_match_score():
    from backend.app.agents.tailor import TailorAgent

    agent = TailorAgent.__new__(TailorAgent)
    # job.match_score (90%) is close to the deterministic score below (85%) —
    # if the bug were still present, no diagnosis-worthy gap would be passed
    # through at all, masking the real 82-vs-57-style gap that matters.
    job = _make_job(match_score=0.90)
    resume_version = ResumeVersion(job_id=job.id, content_json={}, ats_score=0.82, changes_summary="")

    with patch("backend.app.agents.tailor.simulate_ats") as mock_simulate:
        mock_simulate.return_value = MagicMock(
            deterministic_ats_score=57.0, model_dump=lambda: {}, keyword_match=MagicMock(misses=[]),
        )
        agent._score_deterministically(job, _make_profile(), Path("/fake/resume.pdf"), resume_version)

    _, kwargs = mock_simulate.call_args
    assert kwargs["llm_ats_pct"] == 82.0  # resume_version.ats_score * 100, not job.match_score * 100
