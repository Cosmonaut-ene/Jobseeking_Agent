"""Literal keyword matching engine — SPEC 附录 F.5 TASK-C02.

Simulates the string/word-boundary level keyword filters many real ATS
systems actually use, deliberately WITHOUT semantic similarity — that's
already covered elsewhere by the LLM's qualitative gap analysis (Scout).
This module's entire value is being the literal, unforgiving counterpart
that a semantically-generous LLM will never produce on its own.
"""
from __future__ import annotations

import re

from pydantic import BaseModel

from backend.app.ats.aliases import get_alias_group


class KeywordMatchReport(BaseModel):
    score: float  # 0-100，命中率
    hits: list[str]
    misses: list[str]
    alias_hits: list[tuple[str, str]]  # (原始 keyword, 实际命中的别名形式)


def _contains_term(text: str, term: str) -> bool:
    """大小写不敏感、词边界感知的字面匹配（`Java` 不得命中 `JavaScript`）。"""
    if not term:
        return False
    pattern = re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.IGNORECASE)
    return pattern.search(text) is not None


def match_keywords(jd_text: str, resume_text: str, keywords: list[str]) -> KeywordMatchReport:
    """确定性字面/别名匹配，同一输入永远得到同一结果，不做语义相似度。

    keywords 通常来自 Scout 已产出的 gap_analysis.resume_improvements.ats_keywords。
    jd_text 当前版本不参与判定（keywords 已是从 JD 中提炼出的结果），保留该参数
    是为了不强迫调用方在 Scout 契约和本模块之间做额外转换，为未来按 JD 内出现
    频率加权留出扩展空间，但本 Task 范围内不实现加权。
    """
    hits: list[str] = []
    misses: list[str] = []
    alias_hits: list[tuple[str, str]] = []

    for keyword in keywords:
        if not keyword or not keyword.strip():
            continue

        matched_form = next(
            (form for form in get_alias_group(keyword) if _contains_term(resume_text, form)),
            None,
        )
        if matched_form is None:
            misses.append(keyword)
            continue

        hits.append(keyword)
        if matched_form != keyword.strip().lower():
            alias_hits.append((keyword, matched_form))

    total = len(hits) + len(misses)
    score = 100.0 if total == 0 else round(len(hits) / total * 100, 1)

    return KeywordMatchReport(score=score, hits=hits, misses=misses, alias_hits=alias_hits)
