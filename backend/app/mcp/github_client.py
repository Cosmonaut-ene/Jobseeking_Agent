"""GitHub MCP client — SPEC 附录 F.7 TASK-B01.

Talks to GitHub's official *remote* MCP server, not the local Docker
image the README usually leads with — this environment's Docker daemon
is broken (`docker info` segfaults), and the remote endpoint needs no
local process anyway.

Provenance of the details below (2026-08-19):
  - Endpoint URL, auth header, custom X-MCP-* headers, and the tool
    names/parameter shapes are taken from human-verified documentation
    sourced directly from github/github-mcp-server's own README.md and
    docs/remote-server.md — NOT independently fetched by this agent.
  - The MCP Python SDK usage itself (streamable_http_client /
    ClientSession / CallToolResult shape) WAS verified empirically
    against the installed `mcp==2.0.0` package in this environment
    (its actual API differs from what a training-data guess would have
    produced — e.g. the transport function is `streamable_http_client`,
    not `streamablehttp_client`, and headers are set via a pre-built
    httpx2.AsyncClient rather than a `headers=` kwarg).
  - What was NOT verified by anyone yet: an actual live call against
    api.githubcopilot.com — no PAT / no confirmed network egress to
    that host was available while building this. TASK-B01's "四项调用
    均可返回真实数据" AC needs a human to run this against a real
    GITHUB_TOKEN before it can be considered met. See DECISIONS.md.

get_repo_languages() is a known gap: the verified tool list for the
`repos` toolset has no direct "get language stats" tool. It falls back
to a root-directory-listing + filename-extension heuristic, which is
strictly worse than a real per-repo byte-weighted language breakdown.
If a better tool exists that the excerpted docs didn't cover, this
should be revisited.
"""
from __future__ import annotations

import json
import os
from typing import Any

import httpx2
from mcp import ClientSession, types
from mcp.client.streamable_http import streamable_http_client

GITHUB_MCP_URL = "https://api.githubcopilot.com/mcp/"

# 只启用 B01 实际用到的只读工具，缩小配置面（见 X-MCP-Tools，核实文档 §一）
_ALLOWED_TOOLS = "get_me,search_repositories,get_file_contents,list_commits"

_EXT_LANGUAGE_MAP = {
    ".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript",
    ".js": "JavaScript", ".jsx": "JavaScript", ".go": "Go", ".rs": "Rust",
    ".java": "Java", ".rb": "Ruby", ".php": "PHP", ".cs": "C#",
    ".cpp": "C++", ".c": "C", ".swift": "Swift", ".kt": "Kotlin",
}


class GitHubMCPConfigError(Exception):
    """配置类错误——token 缺失/工具名非法，调用方应视为 4xx，不是 500。"""


class GitHubMCPRuntimeError(Exception):
    """运行时错误——工具执行成功连接但返回 isError（404、权限不足等）。"""


def _require_token() -> str:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise GitHubMCPConfigError("GITHUB_TOKEN not configured.")
    return token


def _extract_text(result: types.CallToolResult) -> str:
    parts = [c.text for c in result.content if isinstance(c, types.TextContent)]
    return "\n".join(parts)


def _parse_result(result: types.CallToolResult) -> Any:
    if result.structured_content is not None:
        return result.structured_content
    text = _extract_text(result)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


async def _call_tool(tool_name: str, arguments: dict[str, Any]) -> Any:
    """建立一次性 MCP session 调用单个工具。GitHub 官方远程 server 是无状态友好
    的 stateless streamable-http，每次调用重新握手比维护长连接简单可靠。"""
    token = _require_token()
    http_client = httpx2.AsyncClient(
        headers={
            "Authorization": f"Bearer {token}",
            "X-MCP-Tools": _ALLOWED_TOOLS,
            "X-MCP-Readonly": "true",
        }
    )
    async with streamable_http_client(GITHUB_MCP_URL, http_client=http_client) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            if result.is_error:
                raise GitHubMCPRuntimeError(f"{tool_name} failed: {_extract_text(result)}")
            return _parse_result(result)


async def get_current_user() -> dict:
    """对应 context toolset 的 get_me（官方文档标注"强烈建议启用"）。"""
    result = await _call_tool("get_me", {})
    return result if isinstance(result, dict) else {}


async def list_repos(username: str | None = None, exclude_forks: bool = True) -> list[dict]:
    """列出用户仓库。

    repos toolset 里没有直接的"list repos"工具（已核实文档确认），用
    search_repositories(query="user:<username>") 代替——这是 GitHub 官方文档
    里明确给出的等价做法，不是本模块自己拍脑袋想的变通。
    """
    if username is None:
        me = await get_current_user()
        username = me.get("login")
        if not username:
            raise GitHubMCPRuntimeError("Could not resolve current GitHub username from get_me().")

    query = f"user:{username}"
    if exclude_forks:
        query += " fork:false"

    result = await _call_tool("search_repositories", {"query": query, "minimal_output": True})
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        return result.get("items", []) or result.get("repositories", [])
    return []


async def get_recent_commits(
    owner: str, repo: str, since: str | None = None, author: str | None = None
) -> list[dict]:
    args: dict[str, Any] = {"owner": owner, "repo": repo}
    if since:
        args["since"] = since
    if author:
        args["author"] = author
    result = await _call_tool("list_commits", args)
    return result if isinstance(result, list) else (result or {}).get("commits", [])


async def read_readme(owner: str, repo: str) -> str | None:
    """README 内容；文件不存在是正常场景（不是每个仓库都有 README），返回
    None 而不是抛异常——调用方不该把"没有 README"当成运行时错误处理。
    """
    try:
        result = await _call_tool("get_file_contents", {"owner": owner, "repo": repo, "path": "README.md"})
    except GitHubMCPRuntimeError:
        return None
    if isinstance(result, dict):
        return result.get("content") or result.get("text")
    return str(result) if result else None


async def get_repo_languages(owner: str, repo: str) -> list[str]:
    """技术栈粗略推断，见模块 docstring 顶部"已知缺口"说明——精度低于真实的
    按字节数加权的语言统计，仅供 B02 参考，不作为唯一依据。
    """
    try:
        listing = await _call_tool("get_file_contents", {"owner": owner, "repo": repo, "path": ""})
    except GitHubMCPRuntimeError:
        return []
    entries = listing if isinstance(listing, list) else (listing or {}).get("entries", [])
    names = [e.get("name", "") if isinstance(e, dict) else str(e) for e in entries]
    return _infer_languages_from_filenames(names)


def _infer_languages_from_filenames(names: list[str]) -> list[str]:
    found: set[str] = set()
    for name in names:
        for ext, lang in _EXT_LANGUAGE_MAP.items():
            if name.endswith(ext):
                found.add(lang)
    return sorted(found)
