"""
Tailor Agent — 根据 JD 定制简历。

约束：
  - LLM 只能改写措辞，不能添加 source bullet 中没有的事实/技术/数字
  - 每个输出 bullet 必须携带 source_raw（原始锚点），供人工 review
"""

import json
import logging
import os
import re
from typing import Callable

from google import genai
from google.genai import types

from backend.app import config
from backend.app.ats.simulator import find_latest_uploaded_resume, flatten_resume_version_text, simulate_ats
from backend.app.database import get_session
from backend.app.models.job import Job
from backend.app.models.resume_version import ResumeVersion
from backend.app.models.user_profile import UserProfile

_logger = logging.getLogger(__name__)

# 匹配数字（含百分比、货币、倍数等），用于检测 rewritten 中新增的数字
_NUMBER_RE = re.compile(r"\b\d+\.?\d*\s*[%xk$+]?\b")

MODEL = "gemini-2.5-flash"

TAILOR_SYSTEM = """You are an expert resume writer helping tailor a candidate's resume for a specific job.

STRICT RULES — violation will cause the resume to be rejected:
1. Each rewritten bullet MUST be derived from its source_raw text.
   Do NOT fabricate new experiences, roles, or accomplishments not in source_raw.
   You MAY incorporate exact JD keywords and terminology from the "Target ATS Keywords"
   section below into existing bullets where contextually appropriate.
2. You MAY: rephrase, reorder clauses, emphasise keywords from the JD, use stronger action verbs.
3. Keep each bullet concise: 1–2 lines, starting with a strong past-tense action verb.
4. summary: 2–3 sentences tailored to the role. Only use facts from the candidate profile.
5. selected_skills: ordered by relevance to the JD, max 12 items.
6. Prioritise weaving "Target ATS Keywords" naturally into bullets.
   Prioritise bullets where "Quantification Opportunities" apply."""

ATS_EVAL_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "ats_pct": types.Schema(type=types.Type.INTEGER),
    },
    required=["ats_pct"],
)

TAILOR_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "summary": types.Schema(type=types.Type.STRING),
        "selected_skills": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(type=types.Type.STRING),
        ),
        "tailored_projects": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "name": types.Schema(type=types.Type.STRING),
                    "bullets": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "rewritten": types.Schema(type=types.Type.STRING),
                                "source_raw": types.Schema(type=types.Type.STRING),
                            },
                            required=["rewritten", "source_raw"],
                        ),
                    ),
                },
                required=["name", "bullets"],
            ),
        ),
        "changes_summary": types.Schema(type=types.Type.STRING),
    },
    required=["summary", "selected_skills", "tailored_projects", "changes_summary"],
)


class TailorAgent:
    def __init__(self, max_iterations: int | None = None, deterministic_threshold: float | None = None) -> None:
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self.max_iterations = max_iterations if max_iterations is not None else config.TAILOR_MAX_ITERATIONS
        self.deterministic_threshold = (
            deterministic_threshold
            if deterministic_threshold is not None
            else config.TAILOR_DETERMINISTIC_THRESHOLD
        )

    def run(
        self,
        job: Job,
        user_profile: UserProfile,
        on_progress: Callable[[int, int, float], None] | None = None,
    ) -> ResumeVersion:
        """有界 Evaluator-Optimizer 迭代（SPEC 附录 F.5 TASK-C04）。

        生成 → 确定性评分 → 若低于阈值携带缺失关键词反馈重写 → 重新评分，
        最多 self.max_iterations 轮。反馈信号与停止条件都用**确定性分数**
        （deterministic_ats_score），不用 LLM 自评的 ats_score 驱动——避免
        "用一个模型的主观判断评估另一个模型的主观判断"。

        每一轮都会**独立落库**（本方法自己持久化，调用方不需要再 add/commit），
        不覆盖历史版本——每轮都是一条新的 ResumeVersion 记录，最终只返回
        deterministic_ats_score 最高的一版，但其余轮次的记录仍保留在数据库里。
        没有已上传的简历文件时无法计算确定性分数，退化为单轮、不迭代。

        on_progress(round_num, max_iterations, deterministic_ats_score) 在每轮
        持久化后调用一次——单轮耗时约 30~50 秒（2 次 LLM 调用），实测整趟下来
        可能超过 90 秒，调用方（jobs 路由的后台任务）用它给用户展示实时轮次
        进度，而不是让按钮停在一个死的 "Tailoring…" 上。
        """
        resume_file = self._find_resume_file()
        versions: list[ResumeVersion] = []
        feedback_keywords: list[str] | None = None

        for round_num in range(1, self.max_iterations + 1):
            resume_version = self._run_one_round(job, user_profile, feedback_keywords)

            if resume_file is not None:
                score, report, misses = self._score_deterministically(
                    job, user_profile, resume_file, resume_version
                )
                resume_version.deterministic_ats_score = score
                resume_version.ats_report = report
                feedback_keywords = misses

            # 每轮独立落库——不得覆盖历史版本（每个 ResumeVersion 有自己的 UUID 主键）
            with get_session() as session:
                session.add(resume_version)
                session.commit()
                session.refresh(resume_version)

            versions.append(resume_version)
            _logger.info(
                "[Tailor] Job %s round %d/%d: ats_score=%.2f deterministic_ats_score=%.1f",
                job.id, round_num, self.max_iterations,
                resume_version.ats_score, resume_version.deterministic_ats_score,
            )
            if on_progress and resume_file is not None:
                # 没有已上传简历时算不出确定性分数，此时上报 0% 只会误导用户
                # 以为真的评了 0 分，不如干脆不报——反正这种情况本来就不迭代。
                on_progress(round_num, self.max_iterations, resume_version.deterministic_ats_score)

            if resume_file is None:
                break  # 无法算确定性分数，没有反馈依据，不迭代
            if resume_version.deterministic_ats_score >= self.deterministic_threshold:
                break
            if not feedback_keywords:
                break  # 没有缺失关键词可反馈，再迭代也不会产生新信息

        best = max(versions, key=lambda v: v.deterministic_ats_score)
        _logger.info(
            "[Tailor] Job %s completed %d round(s), selected version deterministic_ats_score=%.1f",
            job.id, len(versions), best.deterministic_ats_score,
        )
        return best

    def _find_resume_file(self):
        return find_latest_uploaded_resume(config.RESUMES_DIR)

    def _run_one_round(
        self, job: Job, user_profile: UserProfile, feedback_keywords: list[str] | None
    ) -> ResumeVersion:
        result = self._tailor(job, user_profile, feedback_keywords=feedback_keywords)
        ats_score = self._eval_ats_score(result, job.raw_jd) / 100

        # Post-process: detect numbers added by LLM that aren't in source_raw.
        # Runs every round, unconditionally — never skipped because of iteration.
        validation_warnings = _validate_bullets(result)
        changes_summary = result["changes_summary"]
        if validation_warnings:
            warning_block = "\n\n[VALIDATION WARNINGS]\n" + "\n".join(
                f"- {w}" for w in validation_warnings
            )
            changes_summary += warning_block
            for w in validation_warnings:
                _logger.warning("Tailor fabrication check: %s", w)

        content_json = {
            "name": user_profile.name,
            "summary": result["summary"],
            "skills": result["selected_skills"],
            "projects": result["tailored_projects"],
            # experience passed through unchanged (empty for now)
            "experience": [
                {
                    "company": exp.company,
                    "role": exp.role,
                    "duration": exp.duration,
                    "bullets": [b.raw for b in exp.bullets],
                }
                for exp in user_profile.experience
            ],
        }

        return ResumeVersion(
            job_id=job.id,
            content_json=content_json,
            ats_score=ats_score,
            changes_summary=changes_summary,
        )

    def _score_deterministically(self, job, user_profile, resume_file, resume_version):
        """返回 (deterministic_ats_score, ats_report dict, keyword misses)。"""
        ats_keywords = job.gap_analysis.get("resume_improvements", {}).get("ats_keywords", [])
        resume_text = flatten_resume_version_text(resume_version.content_json)
        llm_ats_pct = job.match_score * 100 if job.match_score else None

        report = simulate_ats(
            resume_file_path=resume_file,
            profile=user_profile,
            jd_text=job.raw_jd,
            ats_keywords=ats_keywords,
            resume_text=resume_text,
            llm_ats_pct=llm_ats_pct,
        )
        return report.deterministic_ats_score, report.model_dump(), report.keyword_match.misses

    def _tailor(
        self, job: Job, user_profile: UserProfile, feedback_keywords: list[str] | None = None
    ) -> dict:
        profile_text = user_profile.to_prompt_text()
        resume_improvements = job.gap_analysis.get("resume_improvements", {})
        ats_keywords: list[str] = resume_improvements.get("ats_keywords", [])
        metrics_suggestions: list[str] = resume_improvements.get("metrics_suggestions", [])

        feedback_block = ""
        if feedback_keywords:
            feedback_block = (
                "\n## Previous Attempt Feedback\n"
                "The previous version was missing these exact keywords (confirmed by literal "
                "string match against your output, not a guess) — make sure this version "
                "actually contains them verbatim, where truthful and contextually appropriate:\n"
                f"{', '.join(feedback_keywords)}\n"
            )

        prompt = (
            f"## Job Description\n{job.raw_jd}\n\n"
            f"## Required Skills (from JD)\n{', '.join(job.skills_required)}\n\n"
            f"## Gap Analysis\n"
            f"Strong matches: {', '.join(job.gap_analysis.get('strong_matches', []))}\n"
            f"Missing skills: {', '.join(job.gap_analysis.get('missing_skills', []))}\n\n"
            f"## Target ATS Keywords (incorporate these into bullets where appropriate)\n"
            f"{', '.join(ats_keywords)}\n\n"
            f"## Quantification Opportunities\n"
            f"{chr(10).join('- ' + s for s in metrics_suggestions)}\n"
            f"{feedback_block}\n"
            f"## Candidate Profile\n{profile_text}\n\n"
            "Tailor the resume for this job. Select the most relevant projects and rewrite "
            "their bullets to align with the JD keywords. Follow the strict rules."
        )
        response = self.client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=TAILOR_SYSTEM,
                response_mime_type="application/json",
                response_schema=TAILOR_SCHEMA,
            ),
        )
        return json.loads(response.text)

    def _eval_ats_score(self, result: dict, raw_jd: str) -> int:
        resume_text = "\n".join([
            result.get("summary", ""),
            "Skills: " + ", ".join(result.get("selected_skills", [])),
            "\n".join(
                b["rewritten"]
                for proj in result.get("tailored_projects", [])
                for b in proj.get("bullets", [])
            ),
        ])
        prompt = (
            f"## Tailored Resume\n{resume_text}\n\n"
            f"## Job Description\n{raw_jd}\n\n"
            "Return the ATS keyword match percentage (0–100) of the tailored resume against the job description."
        )
        response = self.client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ATS_EVAL_SCHEMA,
            ),
        )
        return json.loads(response.text).get("ats_pct", 0)


def _validate_bullets(tailored: dict) -> list[str]:
    """检测 rewritten bullet 中是否出现 source_raw 没有的数字。

    LLM 被要求不捏造数据，但这个约束只在 prompt 层面。此函数在代码层面做
    一次后处理校验：提取 rewritten 和 source_raw 中的数字，若 rewritten 出现
    了 source_raw 中没有的数字，则视为疑似幻觉并记录 warning。

    不阻断主流程——仅返回警告描述列表，由调用方决定如何处理。
    """
    warnings: list[str] = []
    for project in tailored.get("tailored_projects", []):
        project_name = project.get("name", "unknown")
        for bullet in project.get("bullets", []):
            rewritten: str = bullet.get("rewritten", "")
            source_raw: str = bullet.get("source_raw", "")

            new_numbers = set(_NUMBER_RE.findall(rewritten))
            src_numbers = set(_NUMBER_RE.findall(source_raw))
            added = new_numbers - src_numbers
            if added:
                warnings.append(
                    f"[{project_name}] numbers {sorted(added)} appear in "
                    f"rewritten but not in source_raw"
                )
    return warnings
