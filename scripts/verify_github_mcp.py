#!/usr/bin/env python3
"""Manual verification script for TASK-B01 (backend/app/mcp/github_client.py).

Not a pytest test — those all mock _call_tool by design (no live
network). This script makes real calls against GitHub's remote MCP
server using GITHUB_TOKEN from .env, to confirm the AC that pytest
can't: "四项调用均可返回真实数据".

Usage:
  python3 scripts/verify_github_mcp.py [github-username]

If no username is given, resolves the token owner via get_me().
Prints results only — never prints the token itself.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from dotenv import load_dotenv
load_dotenv()

from backend.app.mcp import github_client as gc


async def main() -> None:
    username = sys.argv[1] if len(sys.argv) > 1 else None

    print("=== get_current_user() ===")
    try:
        me = await gc.get_current_user()
        print(f"OK — login={me.get('login')!r}")
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")
        return

    print("\n=== list_repos() ===")
    try:
        repos = await gc.list_repos(username=username)
        print(f"OK — {len(repos)} repo(s) found")
        for r in repos[:5]:
            name = r.get("full_name") or r.get("name")
            print(f"   - {name}")
        if len(repos) > 5:
            print(f"   ... and {len(repos) - 5} more")
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")
        repos = []

    if not repos:
        print("\nNo repos to test get_recent_commits/read_readme/get_repo_languages against — stopping here.")
        return

    sample = repos[0]
    owner = (sample.get("full_name") or "").split("/")[0] or username or me.get("login")
    repo_name = sample.get("name") or (sample.get("full_name") or "").split("/")[-1]
    print(f"\n(Using {owner}/{repo_name} for the remaining checks)")

    print(f"\n=== get_recent_commits({owner}, {repo_name}) ===")
    try:
        commits = await gc.get_recent_commits(owner, repo_name)
        print(f"OK — {len(commits)} commit(s)")
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")

    print(f"\n=== read_readme({owner}, {repo_name}) ===")
    try:
        readme = await gc.read_readme(owner, repo_name)
        if readme:
            print(f"OK — {len(readme)} chars, starts with: {readme[:60]!r}")
        else:
            print("OK — no README found (returned None, not an error)")
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")

    print(f"\n=== get_repo_languages({owner}, {repo_name}) ===")
    try:
        langs = await gc.get_repo_languages(owner, repo_name)
        print(f"OK — inferred: {langs}")
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
