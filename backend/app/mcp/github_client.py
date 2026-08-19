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
  - 2026-08-19 update: live-verified against a real GITHUB_TOKEN
    (`scripts/verify_github_mcp.py`) — all 5 calls returned real data.
    That run caught a real bug: `get_file_contents` on a single file
    returns a `TextContent` status message ("successfully downloaded
    text file...") *plus* an `EmbeddedResource` block whose
    `resource.text` holds the actual content — the original
    `_parse_result()` only read `TextContent` blocks and returned the
    status message as if it were the file. Fixed below; see DEC-06.
  - Also replaced the `get_repo_languages()` heuristic (root-directory
    listing + filename-extension guessing) with `search_repositories`'
    real `language` field, confirmed present in live responses — more
    accurate and one fewer round trip. See DEC-06 for what this still
    doesn't cover (single primary language per repo, not a full
    per-file byte-weighted breakdown — no MCP tool exposes that).
  - The same live run caught a second bug via a real 422 (bad
    username): anyio TaskGroups inside streamable_http_client /
    ClientSession wrap ANY exception raised in their scope in nested
    BaseExceptionGroups, so a plain GitHubMCPRuntimeError came out
    3-deep-wrapped — `except GitHubMCPRuntimeError` at any call site
    would never have fired. Fixed with `_unwrap_exception_group()`.

TASK-B01's AC ("四项调用均可返回真实数据") is now met — verified live,
not just claimed. See DEC-06 for full details of both fixes.
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

    # get_file_contents on a single file returns a TextContent status
    # message ("successfully downloaded text file...") PLUS an
    # EmbeddedResource block whose .resource.text holds the actual file
    # content — confirmed via a live call (see module docstring / DEC-06).
    # The real content lives here, not in the TextContent block.
    for block in result.content:
        if isinstance(block, types.EmbeddedResource):
            resource_text = getattr(block.resource, "text", None)
            if resource_text is not None:
                return resource_text

    text = _extract_text(result)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _unwrap_exception_group(exc: BaseException) -> BaseException:
    """streamable_http_client / ClientSession both run their internals inside
    anyio TaskGroups, which ALWAYS wrap any exception raised in their scope in
    a BaseExceptionGroup — confirmed live: a plain GitHubMCPRuntimeError from
    a real 422 came out wrapped three levels deep. `except GitHubMCPRuntimeError`
    at the call site would never fire without this unwrap. Only single-cause
    groups are unwrapped; a genuine multi-error group is left as-is since
    collapsing it would hide real concurrent failures.
    """
    while isinstance(exc, BaseExceptionGroup) and len(exc.exceptions) == 1:
        exc = exc.exceptions[0]
    return exc


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
    try:
        async with streamable_http_client(GITHUB_MCP_URL, http_client=http_client) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                if result.is_error:
                    raise GitHubMCPRuntimeError(f"{tool_name} failed: {_extract_text(result)}")
                return _parse_result(result)
    except BaseExceptionGroup as eg:
        raise _unwrap_exception_group(eg) from eg


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

    真实内容来自 _parse_result 从 EmbeddedResource 块里取出的字符串（见该
    函数注释）；单文件请求下 result 就是纯文本，不是 dict。
    """
    try:
        result = await _call_tool("get_file_contents", {"owner": owner, "repo": repo, "path": "README.md"})
    except GitHubMCPRuntimeError:
        return None
    if isinstance(result, dict):
        return result.get("content") or result.get("text")
    return str(result) if result else None


async def get_repo_languages(owner: str, repo: str) -> list[str]:
    """技术栈推断——用 search_repositories(query="repo:{owner}/{repo}") 取
    GitHub 自己判定的主语言（.language 字段，实测确认真实响应里存在，见
    DEC-06）。这是 GitHub 判定的单一"主语言"，不是逐文件按字节数加权的完整
    语言分布（真实 REST /repos/{owner}/{repo}/languages 端点能给，但这个
    MCP server 暴露的工具集里没有对应工具）。
    """
    result = await _call_tool("search_repositories", {"query": f"repo:{owner}/{repo}", "minimal_output": True})
    items = result.get("items", []) if isinstance(result, dict) else []
    if not items:
        return []
    language = items[0].get("language")
    return [language] if language else []
