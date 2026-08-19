"""Tests for the Profile Sync Agent (SPEC 附录 F.7 TASK-B02).

Mocks backend.app.mcp.github_client's public functions (list_repos,
get_repo_languages, read_file, get_recent_commits) — these tests verify
the inference/aggregation logic, not a live connection (that's covered
separately by scripts/verify_github_mcp.py against a real account,
which caught two real bugs during development — see DECISIONS.md
DEC-06 and the regression tests in test_mcp_github_client.py).
"""
import asyncio
from datetime import datetime, timezone
from unittest.mock import patch

from backend.app.agents import profile_sync as ps
from backend.app.mcp import github_client as gc


def _run(coro):
    return asyncio.run(coro)


class TestParsePackageJson:
    def test_extracts_dependencies_and_dev_dependencies(self):
        content = '{"dependencies": {"react": "^18.0.0"}, "devDependencies": {"vite": "^5.0.0"}}'
        assert ps._parse_package_json(content) == {"react", "vite"}

    def test_invalid_json_returns_empty_set(self):
        assert ps._parse_package_json("not json") == set()

    def test_non_dict_json_returns_empty_set(self):
        assert ps._parse_package_json("[1, 2, 3]") == set()

    def test_missing_dependency_keys_returns_empty_set(self):
        assert ps._parse_package_json('{"name": "foo"}') == set()


class TestParsePyprojectToml:
    def test_extracts_project_dependencies_with_version_specifiers_stripped(self):
        content = '[project]\ndependencies = ["fastapi>=0.100", "sqlmodel==0.0.22"]\n'
        assert ps._parse_pyproject_toml(content) == {"fastapi", "sqlmodel"}

    def test_extracts_poetry_dependencies_excluding_python(self):
        content = '[tool.poetry.dependencies]\npython = "^3.12"\nrequests = "^2.0"\n'
        assert ps._parse_pyproject_toml(content) == {"requests"}

    def test_invalid_toml_returns_empty_set(self):
        assert ps._parse_pyproject_toml("not [ valid toml") == set()


class TestParseRequirementsTxt:
    def test_extracts_package_names_strips_version_specifiers(self):
        content = "fastapi>=0.100.0\nsqlmodel==0.0.22\n"
        assert ps._parse_requirements_txt(content) == {"fastapi", "sqlmodel"}

    def test_skips_comments_and_editable_installs(self):
        content = "# a comment\n-e git+https://example.com/foo.git\nrequests\n"
        assert ps._parse_requirements_txt(content) == {"requests"}

    def test_skips_blank_lines(self):
        content = "\n\nrequests\n\n"
        assert ps._parse_requirements_txt(content) == {"requests"}


class TestRepoActivitySpan:
    def test_uses_created_at_and_most_recent_commit_date(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        repo_meta = {"created_at": "2024-01-01T00:00:00Z", "updated_at": "2024-06-01T00:00:00Z"}

        async def fake_get_recent_commits(owner, repo):
            return [{"commit": {"author": {"date": "2024-08-01T00:00:00Z"}}}]

        with patch.object(gc, "get_recent_commits", side_effect=fake_get_recent_commits):
            first, last = _run(ps._repo_activity_span("octocat", "repo1", repo_meta))

        assert first == datetime(2024, 1, 1, tzinfo=timezone.utc)
        assert last == datetime(2024, 8, 1, tzinfo=timezone.utc)

    def test_falls_back_to_updated_at_when_no_commits(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        repo_meta = {"created_at": "2024-01-01T00:00:00Z", "updated_at": "2024-06-01T00:00:00Z"}

        async def fake_get_recent_commits(owner, repo):
            return []

        with patch.object(gc, "get_recent_commits", side_effect=fake_get_recent_commits):
            first, last = _run(ps._repo_activity_span("octocat", "repo1", repo_meta))

        assert last == datetime(2024, 6, 1, tzinfo=timezone.utc)

    def test_falls_back_to_updated_at_when_commits_call_fails(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        repo_meta = {"created_at": "2024-01-01T00:00:00Z", "updated_at": "2024-06-01T00:00:00Z"}

        async def fake_get_recent_commits(owner, repo):
            raise gc.GitHubMCPRuntimeError("boom")

        with patch.object(gc, "get_recent_commits", side_effect=fake_get_recent_commits):
            first, last = _run(ps._repo_activity_span("octocat", "repo1", repo_meta))

        assert last == datetime(2024, 6, 1, tzinfo=timezone.utc)

    def test_clamps_last_active_to_first_seen_when_commit_predates_creation(self, monkeypatch):
        """Regression test for a real bug found live: a repo pushed with
        pre-existing local git history can have a commit author date earlier
        than the GitHub repo's own created_at — completely legitimate, not
        corrupt data. Without a clamp this produces a nonsensical
        last_active < first_seen in the report, undermining traceability."""
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        repo_meta = {"created_at": "2026-04-01T08:16:04Z", "updated_at": "2026-04-01T08:18:22Z"}

        async def fake_get_recent_commits(owner, repo):
            return [{"commit": {"author": {"date": "2026-03-31T23:00:00Z"}}}]  # before created_at

        with patch.object(gc, "get_recent_commits", side_effect=fake_get_recent_commits):
            first, last = _run(ps._repo_activity_span("octocat", "repo1", repo_meta))

        assert last >= first
        assert last == first  # clamped exactly to first_seen, not left inverted


class TestInferRepoTechnologies:
    def test_combines_languages_and_dependency_files(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")

        async def fake_get_repo_languages(owner, repo):
            return ["Python"]

        async def fake_read_file(owner, repo, path):
            if path == "requirements.txt":
                return "fastapi>=0.100\n"
            return None

        with patch.object(gc, "get_repo_languages", side_effect=fake_get_repo_languages), \
             patch.object(gc, "read_file", side_effect=fake_read_file):
            techs = _run(ps._infer_repo_technologies("octocat", "repo1"))

        assert techs == {"Python", "fastapi"}

    def test_tolerates_individual_dependency_file_failures(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")

        async def fake_get_repo_languages(owner, repo):
            return ["Python"]

        async def fake_read_file(owner, repo, path):
            raise gc.GitHubMCPRuntimeError("boom")

        with patch.object(gc, "get_repo_languages", side_effect=fake_get_repo_languages), \
             patch.object(gc, "read_file", side_effect=fake_read_file):
            techs = _run(ps._infer_repo_technologies("octocat", "repo1"))

        assert techs == {"Python"}

    def test_tolerates_language_lookup_failure(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")

        async def fake_get_repo_languages(owner, repo):
            raise gc.GitHubMCPRuntimeError("boom")

        async def fake_read_file(owner, repo, path):
            return None

        with patch.object(gc, "get_repo_languages", side_effect=fake_get_repo_languages), \
             patch.object(gc, "read_file", side_effect=fake_read_file):
            techs = _run(ps._infer_repo_technologies("octocat", "repo1"))

        assert techs == set()


class TestBuildInferredSkill:
    def test_aggregates_across_repos_using_full_span_not_sum(self):
        """Same skill in two repos: years must reflect earliest-to-latest
        span across both, not the sum of each repo's individual duration."""
        observations = [
            ("octocat/repo1", datetime(2020, 1, 1, tzinfo=timezone.utc), datetime(2020, 6, 1, tzinfo=timezone.utc)),
            ("octocat/repo2", datetime(2022, 1, 1, tzinfo=timezone.utc), datetime(2023, 1, 1, tzinfo=timezone.utc)),
        ]
        skill = ps._build_inferred_skill("Python", observations)

        assert skill.first_seen == "2020-01-01"
        assert skill.last_active == "2023-01-01"
        assert skill.source_repos == ["octocat/repo1", "octocat/repo2"]
        # ~3 years span (2020-01-01 to 2023-01-01), not 0.4 + 1.0 summed
        assert 2.9 < skill.years < 3.1

    def test_floors_years_at_minimum_for_near_instant_repos(self):
        observations = [("octocat/repo1", datetime(2024, 1, 1, tzinfo=timezone.utc), datetime(2024, 1, 1, tzinfo=timezone.utc))]
        skill = ps._build_inferred_skill("Rust", observations)
        assert skill.years == ps._MIN_YEARS

    def test_deduplicates_source_repos(self):
        dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
        observations = [("octocat/repo1", dt, dt), ("octocat/repo1", dt, dt)]
        skill = ps._build_inferred_skill("Python", observations)
        assert skill.source_repos == ["octocat/repo1"]


class TestSyncProfile:
    def test_end_to_end_aggregates_across_repos(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")

        async def fake_list_repos(username=None, exclude_forks=True):
            return [
                {"full_name": "octocat/repo1", "created_at": "2020-01-01T00:00:00Z", "updated_at": "2020-06-01T00:00:00Z"},
                {"full_name": "octocat/repo2", "created_at": "2022-01-01T00:00:00Z", "updated_at": "2023-01-01T00:00:00Z"},
            ]

        async def fake_get_repo_languages(owner, repo):
            return ["Python"]

        async def fake_read_file(owner, repo, path):
            return None

        async def fake_get_recent_commits(owner, repo):
            return []

        with patch.object(gc, "list_repos", side_effect=fake_list_repos), \
             patch.object(gc, "get_repo_languages", side_effect=fake_get_repo_languages), \
             patch.object(gc, "read_file", side_effect=fake_read_file), \
             patch.object(gc, "get_recent_commits", side_effect=fake_get_recent_commits):
            skills = _run(ps.sync_profile())

        assert len(skills) == 1
        assert skills[0].name == "Python"
        assert set(skills[0].source_repos) == {"octocat/repo1", "octocat/repo2"}

    def test_skips_repos_with_no_resolvable_owner_repo_name(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")

        async def fake_list_repos(username=None, exclude_forks=True):
            return [{"full_name": ""}, {"name": "no-owner-here"}]

        with patch.object(gc, "list_repos", side_effect=fake_list_repos):
            skills = _run(ps.sync_profile())

        assert skills == []

    def test_passes_exclude_forks_through_to_list_repos(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        captured = {}

        async def fake_list_repos(username=None, exclude_forks=True):
            captured["exclude_forks"] = exclude_forks
            captured["username"] = username
            return []

        with patch.object(gc, "list_repos", side_effect=fake_list_repos):
            _run(ps.sync_profile(username="octocat", exclude_forks=False))

        assert captured == {"exclude_forks": False, "username": "octocat"}
