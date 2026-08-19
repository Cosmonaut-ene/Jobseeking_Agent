"""Tests for the GitHub MCP client wrapper (SPEC 附录 F.7 TASK-B01).

Mocks `_call_tool` — the one function that actually talks to the MCP
server — so these tests verify the wrapper logic (query building,
username resolution via get_me, graceful 404-as-None handling, the
filename-extension language heuristic, result parsing), not a live
connection. No PAT / confirmed network egress to api.githubcopilot.com
was available while building this; a human needs to verify live
behavior separately before TASK-B01's "returns real data" AC is met
(see DECISIONS.md).
"""
import asyncio
from unittest.mock import patch

import pytest

from backend.app.mcp import github_client as gc


def _run(coro):
    return asyncio.run(coro)


class TestTokenRequirement:
    def test_missing_token_raises_config_error(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        with pytest.raises(gc.GitHubMCPConfigError):
            _run(gc.get_current_user())


class TestListRepos:
    def test_resolves_username_via_get_me_when_not_given(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        calls = []

        async def fake_call_tool(tool_name, arguments):
            calls.append((tool_name, arguments))
            if tool_name == "get_me":
                return {"login": "octocat"}
            if tool_name == "search_repositories":
                return {"items": [{"name": "repo1"}]}
            raise AssertionError(f"unexpected tool {tool_name}")

        with patch.object(gc, "_call_tool", side_effect=fake_call_tool):
            repos = _run(gc.list_repos())

        assert repos == [{"name": "repo1"}]
        assert calls[0] == ("get_me", {})
        assert calls[1][0] == "search_repositories"
        assert calls[1][1]["query"] == "user:octocat fork:false"

    def test_uses_given_username_without_calling_get_me(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        calls = []

        async def fake_call_tool(tool_name, arguments):
            calls.append(tool_name)
            return {"items": []}

        with patch.object(gc, "_call_tool", side_effect=fake_call_tool):
            repos = _run(gc.list_repos(username="someone"))

        assert repos == []
        assert calls == ["search_repositories"]

    def test_exclude_forks_false_omits_qualifier(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        captured = {}

        async def fake_call_tool(tool_name, arguments):
            captured.update(arguments)
            return []

        with patch.object(gc, "_call_tool", side_effect=fake_call_tool):
            _run(gc.list_repos(username="octocat", exclude_forks=False))

        assert captured["query"] == "user:octocat"

    def test_raises_runtime_error_when_username_cannot_be_resolved(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")

        async def fake_call_tool(tool_name, arguments):
            return {}  # get_me returns no "login"

        with patch.object(gc, "_call_tool", side_effect=fake_call_tool):
            with pytest.raises(gc.GitHubMCPRuntimeError):
                _run(gc.list_repos())


class TestGetRecentCommits:
    def test_passes_optional_filters(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        captured = {}

        async def fake_call_tool(tool_name, arguments):
            captured.update(arguments)
            return [{"sha": "abc"}]

        with patch.object(gc, "_call_tool", side_effect=fake_call_tool):
            commits = _run(gc.get_recent_commits("octocat", "repo1", since="2026-01-01", author="octocat"))

        assert commits == [{"sha": "abc"}]
        assert captured == {"owner": "octocat", "repo": "repo1", "since": "2026-01-01", "author": "octocat"}

    def test_omits_optional_filters_when_not_given(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        captured = {}

        async def fake_call_tool(tool_name, arguments):
            captured.update(arguments)
            return []

        with patch.object(gc, "_call_tool", side_effect=fake_call_tool):
            _run(gc.get_recent_commits("octocat", "repo1"))

        assert captured == {"owner": "octocat", "repo": "repo1"}


class TestReadReadme:
    def test_returns_content_on_success(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")

        async def fake_call_tool(tool_name, arguments):
            assert arguments["path"] == "README.md"
            return {"content": "# Hello"}

        with patch.object(gc, "_call_tool", side_effect=fake_call_tool):
            readme = _run(gc.read_readme("octocat", "repo1"))

        assert readme == "# Hello"

    def test_returns_none_not_exception_when_file_missing(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")

        async def fake_call_tool(tool_name, arguments):
            raise gc.GitHubMCPRuntimeError("get_file_contents failed: 404 Not Found")

        with patch.object(gc, "_call_tool", side_effect=fake_call_tool):
            readme = _run(gc.read_readme("octocat", "repo1"))

        assert readme is None


class TestGetRepoLanguages:
    def test_infers_languages_from_root_filenames(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")

        async def fake_call_tool(tool_name, arguments):
            return {"entries": [{"name": "main.py"}, {"name": "app.tsx"}, {"name": "README.md"}]}

        with patch.object(gc, "_call_tool", side_effect=fake_call_tool):
            langs = _run(gc.get_repo_languages("octocat", "repo1"))

        assert langs == ["Python", "TypeScript"]

    def test_returns_empty_list_when_repo_unreadable(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")

        async def fake_call_tool(tool_name, arguments):
            raise gc.GitHubMCPRuntimeError("get_file_contents failed: 404")

        with patch.object(gc, "_call_tool", side_effect=fake_call_tool):
            langs = _run(gc.get_repo_languages("octocat", "repo1"))

        assert langs == []


class TestResultParsing:
    def test_extract_text_joins_text_content_blocks(self):
        from mcp import types
        result = types.CallToolResult(
            content=[types.TextContent(type="text", text="hello"), types.TextContent(type="text", text="world")]
        )
        assert gc._extract_text(result) == "hello\nworld"

    def test_parse_result_prefers_structured_content(self):
        from mcp import types
        result = types.CallToolResult(content=[], structuredContent={"a": 1})
        assert gc._parse_result(result) == {"a": 1}

    def test_parse_result_falls_back_to_json_parsing_text(self):
        from mcp import types
        result = types.CallToolResult(content=[types.TextContent(type="text", text='{"login": "octocat"}')])
        assert gc._parse_result(result) == {"login": "octocat"}

    def test_parse_result_returns_raw_text_when_not_json(self):
        from mcp import types
        result = types.CallToolResult(content=[types.TextContent(type="text", text="plain text, not json")])
        assert gc._parse_result(result) == "plain text, not json"
