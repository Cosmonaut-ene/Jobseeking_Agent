"""Tests for the GitHub MCP client wrapper (SPEC 附录 F.7 TASK-B01).

Mocks `_call_tool` — the one function that actually talks to the MCP
server — so most of these tests verify wrapper logic (query building,
username resolution via get_me, graceful 404-as-None handling, result
parsing), not a live connection. Live-verified 2026-08-19 against a
real GITHUB_TOKEN via scripts/verify_github_mcp.py — that run caught
two real bugs neither of these mocked tests could have (mocking
_call_tool bypasses exactly the machinery that was broken):
  1. get_file_contents' real response shape (EmbeddedResource holding
     the actual file content, not the TextContent status message) —
     see test_parse_result_prefers_embedded_resource_over_status_text.
  2. anyio TaskGroup wrapping any exception raised inside
     streamable_http_client/ClientSession in nested ExceptionGroups —
     see TestExceptionGroupUnwrapping.
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
        """_call_tool is mocked here at the wrapper boundary — the real
        EmbeddedResource-vs-TextContent extraction is covered directly in
        TestResultParsing below, against the shape a live call actually
        returned (see module docstring)."""
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")

        async def fake_call_tool(tool_name, arguments):
            assert arguments["path"] == "README.md"
            return "# Hello"  # _parse_result already unwraps EmbeddedResource to a plain string

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
    def test_returns_primary_language_from_search_repositories(self, monkeypatch):
        """Live-verified (scripts/verify_github_mcp.py): search_repositories
        results carry a real `.language` field — used instead of the
        directory-listing heuristic this function started with (see DEC-06)."""
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        captured = {}

        async def fake_call_tool(tool_name, arguments):
            captured["tool_name"] = tool_name
            captured["arguments"] = arguments
            return {"items": [{"full_name": "octocat/repo1", "language": "Python"}]}

        with patch.object(gc, "_call_tool", side_effect=fake_call_tool):
            langs = _run(gc.get_repo_languages("octocat", "repo1"))

        assert langs == ["Python"]
        assert captured["tool_name"] == "search_repositories"
        assert captured["arguments"]["query"] == "repo:octocat/repo1"

    def test_returns_empty_list_when_repo_not_found(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")

        async def fake_call_tool(tool_name, arguments):
            return {"items": []}

        with patch.object(gc, "_call_tool", side_effect=fake_call_tool):
            langs = _run(gc.get_repo_languages("octocat", "repo1"))

        assert langs == []

    def test_returns_empty_list_when_language_field_is_null(self, monkeypatch):
        """Repos with no dominant language (e.g. docs-only) have language: null."""
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")

        async def fake_call_tool(tool_name, arguments):
            return {"items": [{"full_name": "octocat/repo1", "language": None}]}

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

    def test_parse_result_prefers_embedded_resource_over_status_text(self):
        """Regression test for a real bug caught by a live call
        (scripts/verify_github_mcp.py, 2026-08-19): get_file_contents on a
        single file returns a TextContent status message ("successfully
        downloaded text file...") *plus* an EmbeddedResource block holding
        the actual content. The original _parse_result only read
        TextContent and silently returned the status message as if it
        were the file — this locks in the fix against the exact shape a
        live call produced, not a guessed one."""
        from mcp import types

        result = types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text="successfully downloaded text file (SHA: 18bc70ebe277fbfe6e55e6f9a0ae7e2c3e4bdd83)",
                ),
                types.EmbeddedResource(
                    type="resource",
                    resource=types.TextResourceContents(
                        uri="repo://octocat/repo1/sha/abc/contents/README.md",
                        mime_type="text/plain; charset=utf-8",
                        text="# Real Content\n",
                    ),
                ),
            ]
        )

        assert gc._parse_result(result) == "# Real Content\n"


class TestExceptionGroupUnwrapping:
    """Regression coverage for the bug found by scripts/verify_github_mcp.py
    against a real 422 from GitHub: a plain GitHubMCPRuntimeError raised
    inside _call_tool's `async with` block came out as a 3-deep-nested
    BaseExceptionGroup instead — `except GitHubMCPRuntimeError` at any call
    site would never have fired. Unit-tests the unwrap helper directly
    since reproducing the real anyio TaskGroup nesting would require an
    actual network call."""

    def test_unwraps_single_cause_group_to_the_original_exception(self):
        original = gc.GitHubMCPRuntimeError("boom")
        wrapped_once = BaseExceptionGroup("eg", [original])
        wrapped_twice = BaseExceptionGroup("eg", [wrapped_once])
        wrapped_thrice = BaseExceptionGroup("eg", [wrapped_twice])

        assert gc._unwrap_exception_group(wrapped_thrice) is original

    def test_leaves_multi_cause_group_intact(self):
        """A genuine multi-error group must not be silently collapsed —
        that would hide a real concurrent-failure scenario."""
        group = BaseExceptionGroup("eg", [ValueError("a"), ValueError("b")])
        assert gc._unwrap_exception_group(group) is group

    def test_non_group_exception_passes_through_unchanged(self):
        exc = RuntimeError("not a group")
        assert gc._unwrap_exception_group(exc) is exc
