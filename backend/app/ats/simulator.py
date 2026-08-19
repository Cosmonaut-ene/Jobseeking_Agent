"""Composite ATS simulation — SPEC 附录 F.5 TASK-C03.

Aggregates the parseability checker (C01) and keyword match engine (C02)
into a single `deterministic_ats_score`, paired with an actionable
diagnosis when it diverges significantly from the LLM's qualitative
`match_score` (§8.6). Neither sub-score is replaced by the other — both
are always returned, each labelled by its own source.
"""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from backend.app.ats.keyword_match import KeywordMatchReport, match_keywords
from backend.app.ats.parseability import ParseabilityReport, check_parseability
from backend.app.models.user_profile import UserProfile

# 差异解读的触发阈值（百分点）——见 SPEC 附录 F.5 TASK-C03 AC
DIAGNOSIS_DIFF_THRESHOLD = 20.0

# deterministic_ats_score 的加权：解析度是关键词能否被读到的前提，权重略高
_PARSEABILITY_WEIGHT = 0.6
_KEYWORD_MATCH_WEIGHT = 0.4


class ATSSimulationReport(BaseModel):
    deterministic_ats_score: float
    parseability: ParseabilityReport
    keyword_match: KeywordMatchReport
    diagnosis: list[str]  # 仅当与 llm_ats_pct 差异 > 阈值时非空；文案须具体可执行


def simulate_ats(
    resume_file_path: Path | str,
    profile: UserProfile,
    jd_text: str,
    ats_keywords: list[str],
    resume_text: str,
    llm_ats_pct: float | None = None,
) -> ATSSimulationReport:
    """确定性 ATS 模拟：同一 (文件, profile, JD, 关键词, 简历文本) 组合永远得到同一份报告。

    resume_file_path 必须是用户实际上传的简历文件（F-CONF-01），不是系统生成的
    PDF/DOCX——解析度反映的是"这份会被拿去投递的文件"的真实解析风险，与具体某次
    Tailor 输出无关；resume_text 则是某个具体 ResumeVersion 的内容，关键词命中率
    随每次 Tailor 结果变化。
    """
    parseability = check_parseability(resume_file_path, profile)
    keyword_match = match_keywords(jd_text, resume_text, ats_keywords)

    deterministic_score = round(
        parseability.score * _PARSEABILITY_WEIGHT + keyword_match.score * _KEYWORD_MATCH_WEIGHT,
        1,
    )

    return ATSSimulationReport(
        deterministic_ats_score=deterministic_score,
        parseability=parseability,
        keyword_match=keyword_match,
        diagnosis=_build_diagnosis(deterministic_score, parseability, keyword_match, llm_ats_pct),
    )


def _build_diagnosis(
    deterministic_score: float,
    parseability: ParseabilityReport,
    keyword_match: KeywordMatchReport,
    llm_ats_pct: float | None,
) -> list[str]:
    if llm_ats_pct is None or abs(llm_ats_pct - deterministic_score) <= DIAGNOSIS_DIFF_THRESHOLD:
        return []

    diagnosis: list[str] = []
    if keyword_match.score < 70 and keyword_match.misses:
        diagnosis.append(
            f"字面关键词覆盖率仅 {keyword_match.score:.0f}%，"
            f"建议在技能区补充 JD 原词：{'、'.join(keyword_match.misses[:5])}"
        )
    if parseability.score < 70 and parseability.warnings:
        diagnosis.append(
            f"简历解析风险较高（解析度 {parseability.score:.0f}%）：{'；'.join(parseability.warnings[:2])}"
        )
    if not diagnosis:
        diagnosis.append(
            f"AI 定性评分（{llm_ats_pct:.0f}%）与确定性评分（{deterministic_score:.0f}%）"
            "存在较大差距，建议人工复核简历内容与 JD 的实际匹配情况"
        )
    return diagnosis
