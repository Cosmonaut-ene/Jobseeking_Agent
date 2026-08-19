"""Profile Sync Agent — SPEC 附录 F.7 TASK-B02 + TASK-B03.

TASK-B02 (sync_profile): infers a candidate's tech stack and how long
they've used each technology from real GitHub activity — repo
languages (via backend.app.mcp.github_client.get_repo_languages) plus
dependency-file parsing (package.json / pyproject.toml /
requirements.txt) for *what*, and repo creation + real commit
timestamps for *how long* — not an LLM guess.

This directly corrects a known issue in ResumeParser: its `years`
field is model-estimated from resume prose with no ground truth (see
its PARSE_SYSTEM prompt). Here `years` is derived from objective
GitHub timestamps, and every inferred skill keeps first_seen /
last_active / source_repos so the number is traceable, not a black box.

TASK-B03 (build_skill_diff / apply_skill_diff): turns B02's inference
into a reviewable diff against the existing UserProfile.skills, and
applies only the entries a human explicitly accepted. The merge rule
(key by lowercased name, years only ever goes up) is the exact same
rule frontend/src/pages/Resume.tsx's mergeSkills() already uses for
incremental resume-paste merges — re-implemented here in Python with
identical semantics, not a second, different merge policy (SPEC
F-CONF-03: "不得新写一套"). Nothing in this module writes to
UserProfile directly — sync_profile()/build_skill_diff() only infer
and propose; a router endpoint calls apply_skill_diff() only after a
human has picked which entries to accept.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel

from backend.app.mcp import github_client as gc
from backend.app.models.user_profile import Skill

_DEPENDENCY_FILES = ("package.json", "pyproject.toml", "requirements.txt")

# 避免瞬时/单次 commit 仓库算出 0 年经验这种没有信息量的数字
_MIN_YEARS = 0.1

_VERSION_SPEC_RE = re.compile(r"^([A-Za-z0-9_.\-]+)")


class InferredSkill(BaseModel):
    name: str
    years: float
    source_repos: list[str]  # 可回溯性：这个技能是从哪些仓库推断出来的
    first_seen: str  # ISO date — 最早出现该技能的仓库创建时间
    last_active: str  # ISO date — 最近一次相关 commit（或退化为仓库 updated_at）


async def sync_profile(username: str | None = None, exclude_forks: bool = True) -> list[InferredSkill]:
    """扫描用户仓库，推断技术栈 + 各技能的活跃使用时长。

    fork 仓库默认排除（透传给 list_repos，B01 已实现该开关，这里不重新做）。
    """
    repos = await gc.list_repos(username=username, exclude_forks=exclude_forks)

    # tech name -> [(repo_full_name, first_seen, last_active), ...]
    observations: dict[str, list[tuple[str, datetime, datetime]]] = {}

    for repo in repos:
        full_name = repo.get("full_name") or repo.get("name", "")
        owner, _, repo_name = full_name.partition("/")
        if not owner or not repo_name:
            continue

        first_seen, last_active = await _repo_activity_span(owner, repo_name, repo)
        for tech in await _infer_repo_technologies(owner, repo_name):
            observations.setdefault(tech, []).append((full_name, first_seen, last_active))

    return [_build_inferred_skill(name, obs) for name, obs in sorted(observations.items())]


async def _repo_activity_span(owner: str, repo: str, repo_meta: dict) -> tuple[datetime, datetime]:
    """first_seen 用仓库创建时间；last_active 优先用最近一次真实 commit 的
    作者时间戳，拿不到 commit（空仓库/工具调用失败）时退化用仓库 updated_at。

    真实踩过的坑（实测发现）：commit 的作者时间戳可以早于仓库在 GitHub 上的
    created_at——本地先攒一段 git 历史，之后才一次性 push 建库，是完全正常的
    真实场景（不是数据错误）。如果不做下限约束，会算出 last_active 早于
    first_seen，报告里出现"最近活跃日期比首次出现日期还早"这种自相矛盾的
    输出，破坏"可回溯"这个约束的可信度。所以强制 last_active >= first_seen。
    """
    now = datetime.now(timezone.utc)
    first_seen = _parse_dt(repo_meta.get("created_at")) or now
    last_active = _parse_dt(repo_meta.get("updated_at")) or first_seen

    try:
        commits = await gc.get_recent_commits(owner, repo)
    except gc.GitHubMCPRuntimeError:
        commits = []

    if commits:
        commit_date = _parse_dt((commits[0].get("commit") or {}).get("author", {}).get("date"))
        if commit_date:
            last_active = commit_date

    return first_seen, max(last_active, first_seen)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


async def _infer_repo_technologies(owner: str, repo: str) -> set[str]:
    techs: set[str] = set()

    try:
        techs.update(await gc.get_repo_languages(owner, repo))
    except gc.GitHubMCPRuntimeError:
        pass

    for filename in _DEPENDENCY_FILES:
        try:
            content = await gc.read_file(owner, repo, filename)
        except gc.GitHubMCPRuntimeError:
            content = None
        if content:
            techs.update(_parse_dependency_file(filename, content))

    return techs


def _parse_dependency_file(filename: str, content: str) -> set[str]:
    if filename == "package.json":
        return _parse_package_json(content)
    if filename == "pyproject.toml":
        return _parse_pyproject_toml(content)
    if filename == "requirements.txt":
        return _parse_requirements_txt(content)
    return set()


def _parse_package_json(content: str) -> set[str]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return set()
    if not isinstance(data, dict):
        return set()
    names: set[str] = set()
    for key in ("dependencies", "devDependencies"):
        names.update((data.get(key) or {}).keys())
    return names


def _parse_pyproject_toml(content: str) -> set[str]:
    try:
        import tomllib
        data = tomllib.loads(content)
    except Exception:
        return set()
    names: set[str] = set()
    names.update(_strip_version_specifiers(data.get("project", {}).get("dependencies", []) or []))
    poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {}) or {}
    names.update(k for k in poetry_deps.keys() if k.lower() != "python")
    return names


def _parse_requirements_txt(content: str) -> set[str]:
    lines = [line.strip() for line in content.splitlines()]
    lines = [line for line in lines if line and not line.startswith(("#", "-"))]
    return _strip_version_specifiers(lines)


def _strip_version_specifiers(specs: list[str]) -> set[str]:
    names: set[str] = set()
    for spec in specs:
        match = _VERSION_SPEC_RE.match(spec.strip())
        if match:
            names.add(match.group(1).lower())
    return names


def _build_inferred_skill(name: str, observations: list[tuple[str, datetime, datetime]]) -> InferredSkill:
    """跨仓库聚合：同一技能在多个仓库出现时，years 取"最早出现"到"最近活跃"
    的完整跨度，而不是逐仓库时长相加——回答的是"用了这个技能多久"，不是
    "总共花了多少仓库·月"。"""
    first_seen = min(obs[1] for obs in observations)
    last_active = max(obs[2] for obs in observations)
    years = max((last_active - first_seen).days / 365.25, _MIN_YEARS)
    return InferredSkill(
        name=name,
        years=round(years, 1),
        source_repos=sorted({obs[0] for obs in observations}),
        first_seen=first_seen.date().isoformat(),
        last_active=last_active.date().isoformat(),
    )


# ── TASK-B03: diff proposal + human-confirmed merge ──────────────────────────

# 复用 ResumeParser 系统提示词里同样的 years -> level 判定阈值（beginner < 1y,
# intermediate 1-3y, expert 3y+），不新发明一套——GitHub 数据只给得出 years，
# 给不出"是不是被列为主要强项"这种主观信号，所以新技能的 level 只能从 years
# 反推，用项目里已经确立的同一套边界，保持内部一致。
def _infer_level_from_years(years: float) -> str:
    if years >= 3:
        return "expert"
    if years >= 1:
        return "intermediate"
    return "beginner"


class SkillDiffEntry(BaseModel):
    """一条待人工确认的技能变更提议。change_type 只有两种，因为 mergeSkills
    的规则本身只支持这两种变更：新增技能，或已有技能的 years 往上调——years
    变小的推断结果不会产生 diff 条目（按 Resume.tsx 的既有规则，years 只增不
    减，没有变更可提）。"""
    name: str
    change_type: Literal["new", "years_increase"]
    proposed_years: float
    current_years: float | None = None  # "new" 时为 None
    source_repos: list[str]
    first_seen: str
    last_active: str


def build_skill_diff(existing_skills: list[Skill], inferred: list[InferredSkill]) -> list[SkillDiffEntry]:
    """把 B02 的推断结果对照现有 UserProfile.skills，算出"值得提议"的变更。

    合并键与 years 比较规则跟 Resume.tsx::mergeSkills 完全一致：按
    name.lower() 匹配，只有推断值严格大于现有值才算变更。不产出 years 相等
    或更小的条目——那种情况下 mergeSkills 的规则本来就不会改变现有数据，
    提议出来只会让人误以为有什么可确认的。
    """
    existing_map = {s.name.lower(): s for s in existing_skills}
    diffs: list[SkillDiffEntry] = []
    for skill in inferred:
        key = skill.name.lower()
        existing = existing_map.get(key)
        if existing is None:
            diffs.append(SkillDiffEntry(
                name=skill.name,
                change_type="new",
                proposed_years=skill.years,
                current_years=None,
                source_repos=skill.source_repos,
                first_seen=skill.first_seen,
                last_active=skill.last_active,
            ))
        elif skill.years > existing.years:
            diffs.append(SkillDiffEntry(
                name=skill.name,
                change_type="years_increase",
                proposed_years=skill.years,
                current_years=existing.years,
                source_repos=skill.source_repos,
                first_seen=skill.first_seen,
                last_active=skill.last_active,
            ))
    return diffs


def apply_skill_diff(
    existing_skills: list[Skill], diff_entries: list[SkillDiffEntry], accepted_names: set[str]
) -> list[Skill]:
    """只合并人工接受的条目，规则同 mergeSkills：key=name.lower()，
    years=max(现有, 提议)。手动编辑过的字段（level、非 years 部分）不被
    静默覆盖——已有技能只更新 years，level 保持用户原有设置不动；只有全新
    技能才需要从 years 反推一个 level（见 _infer_level_from_years）。

    accepted_names 按大小写不敏感匹配（用户在前端勾选时看到的是原始大小写
    的技能名，这里统一转小写比较，避免"React" vs "react"被当成两个不同的
    技能而漏合并）。
    """
    accepted_keys = {name.lower() for name in accepted_names}
    existing_map = {s.name.lower(): s for s in existing_skills}

    for entry in diff_entries:
        key = entry.name.lower()
        if key not in accepted_keys:
            continue

        current = existing_map.get(key)
        if current is not None:
            existing_map[key] = Skill(
                name=current.name,
                level=current.level,
                years=max(current.years, entry.proposed_years),
            )
        else:
            existing_map[key] = Skill(
                name=entry.name,
                level=_infer_level_from_years(entry.proposed_years),
                years=entry.proposed_years,
            )

    return list(existing_map.values())
