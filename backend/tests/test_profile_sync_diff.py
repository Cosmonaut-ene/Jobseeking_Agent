"""Tests for TASK-B03: build_skill_diff / apply_skill_diff.

Merge semantics must match frontend/src/pages/Resume.tsx::mergeSkills
exactly (key by lowercased name, years only ever goes up) — see
SPEC F-CONF-03 ("不得新写一套") and the module docstring.
"""
from backend.app.agents.profile_sync import (
    InferredSkill,
    SkillDiffEntry,
    apply_skill_diff,
    build_skill_diff,
)
from backend.app.models.user_profile import Skill


def _inferred(name: str, years: float, repos=("octocat/repo1",)) -> InferredSkill:
    return InferredSkill(
        name=name, years=years, source_repos=list(repos),
        first_seen="2024-01-01", last_active="2024-06-01",
    )


class TestBuildSkillDiff:
    def test_new_skill_produces_new_entry(self):
        diff = build_skill_diff([], [_inferred("Python", 2.0)])
        assert len(diff) == 1
        assert diff[0].name == "Python"
        assert diff[0].change_type == "new"
        assert diff[0].proposed_years == 2.0
        assert diff[0].current_years is None

    def test_higher_years_produces_years_increase_entry(self):
        existing = [Skill(name="Python", level="intermediate", years=1.0)]
        diff = build_skill_diff(existing, [_inferred("Python", 3.0)])
        assert len(diff) == 1
        assert diff[0].change_type == "years_increase"
        assert diff[0].current_years == 1.0
        assert diff[0].proposed_years == 3.0

    def test_lower_or_equal_years_produces_no_entry(self):
        existing = [Skill(name="Python", level="expert", years=5.0)]
        diff = build_skill_diff(existing, [_inferred("Python", 2.0)])
        assert diff == []

        diff_equal = build_skill_diff(existing, [_inferred("Python", 5.0)])
        assert diff_equal == []

    def test_matching_is_case_insensitive(self):
        existing = [Skill(name="python", level="expert", years=5.0)]
        diff = build_skill_diff(existing, [_inferred("Python", 6.0)])
        assert len(diff) == 1
        assert diff[0].change_type == "years_increase"

    def test_mixed_new_and_increase_and_no_change(self):
        existing = [
            Skill(name="Python", level="expert", years=5.0),
            Skill(name="Go", level="beginner", years=0.5),
        ]
        inferred = [_inferred("Python", 3.0), _inferred("Go", 2.0), _inferred("Rust", 1.0)]
        diff = build_skill_diff(existing, inferred)
        by_name = {d.name: d for d in diff}
        assert "Python" not in by_name  # 3.0 < 5.0, no change
        assert by_name["Go"].change_type == "years_increase"
        assert by_name["Rust"].change_type == "new"


class TestApplySkillDiff:
    def test_unaccepted_entries_are_not_applied(self):
        existing = []
        diff = [SkillDiffEntry(name="Python", change_type="new", proposed_years=2.0,
                                source_repos=["r1"], first_seen="2024-01-01", last_active="2024-06-01")]
        result = apply_skill_diff(existing, diff, accepted_names=set())
        assert result == []

    def test_accepted_new_skill_gets_inferred_level(self):
        diff = [SkillDiffEntry(name="Rust", change_type="new", proposed_years=3.5,
                                source_repos=["r1"], first_seen="2024-01-01", last_active="2024-06-01")]
        result = apply_skill_diff([], diff, accepted_names={"Rust"})
        assert len(result) == 1
        assert result[0].name == "Rust"
        assert result[0].years == 3.5
        assert result[0].level == "expert"  # >= 3 years

    def test_accepted_years_increase_keeps_existing_level_untouched(self):
        """Manually-edited fields (level) must not be silently overwritten —
        only years changes, and only via max(), never a straight replace."""
        existing = [Skill(name="Python", level="beginner", years=1.0)]  # user manually set "beginner"
        diff = [SkillDiffEntry(name="Python", change_type="years_increase", proposed_years=4.0,
                                current_years=1.0, source_repos=["r1"], first_seen="2024-01-01", last_active="2024-06-01")]
        result = apply_skill_diff(existing, diff, accepted_names={"Python"})
        assert len(result) == 1
        assert result[0].level == "beginner"  # untouched, even though years now imply "expert"
        assert result[0].years == 4.0

    def test_years_never_decreases_even_if_somehow_accepted_with_lower_value(self):
        existing = [Skill(name="Python", level="expert", years=5.0)]
        diff = [SkillDiffEntry(name="Python", change_type="years_increase", proposed_years=3.0,
                                current_years=5.0, source_repos=["r1"], first_seen="2024-01-01", last_active="2024-06-01")]
        result = apply_skill_diff(existing, diff, accepted_names={"Python"})
        assert result[0].years == 5.0  # max(5.0, 3.0), never regresses

    def test_case_insensitive_acceptance_matching(self):
        diff = [SkillDiffEntry(name="Python", change_type="new", proposed_years=2.0,
                                source_repos=["r1"], first_seen="2024-01-01", last_active="2024-06-01")]
        result = apply_skill_diff([], diff, accepted_names={"python"})  # lowercase acceptance
        assert len(result) == 1

    def test_untouched_existing_skills_pass_through_unchanged(self):
        existing = [Skill(name="Go", level="intermediate", years=2.0)]
        result = apply_skill_diff(existing, [], accepted_names=set())
        assert result == existing

    def test_level_boundaries_match_resume_parser_thresholds(self):
        cases = [(0.5, "beginner"), (0.9, "beginner"), (1.0, "intermediate"), (2.9, "intermediate"), (3.0, "expert")]
        for years, expected_level in cases:
            diff = [SkillDiffEntry(name="X", change_type="new", proposed_years=years,
                                    source_repos=["r1"], first_seen="2024-01-01", last_active="2024-06-01")]
            result = apply_skill_diff([], diff, accepted_names={"X"})
            assert result[0].level == expected_level, f"years={years}"
