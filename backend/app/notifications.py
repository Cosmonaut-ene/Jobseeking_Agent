"""Push notifications via HTTP webhook (Telegram Bot API / Discord compatible)."""
import logging
import os
import re
import httpx
from backend.app.models.job import Job

logger = logging.getLogger(__name__)


def _strip_html(text: str) -> str:
    """Remove HTML tags for plain-text webhooks (e.g. Discord)."""
    text = re.sub(r"<a[^>]+>", "", text)
    return re.sub(r"<[^>]+>", "", text)


def _send(text: str) -> bool:
    """Send a message via configured webhook. Returns True on success."""
    webhook_url = os.environ.get("NOTIFICATION_WEBHOOK_URL", "")
    chat_id = os.environ.get("NOTIFICATION_CHAT_ID", "")
    if not webhook_url:
        logger.info("[Notify] No webhook URL configured, skipping push.")
        return False
    try:
        is_discord = "discord.com/api/webhooks" in webhook_url
        if is_discord:
            payload: dict = {"content": _strip_html(text)}
        else:
            payload = {"text": text, "parse_mode": "HTML"}
            if chat_id:
                payload["chat_id"] = chat_id
        r = httpx.post(webhook_url, json=payload, timeout=10)
        r.raise_for_status()
        logger.info("[Notify] Push sent OK (%d)", r.status_code)
        return True
    except Exception as exc:
        logger.error("[Notify] Push failed: %s", exc)
        return False


def push_high_score_job(job: Job) -> bool:
    """Immediate push for jobs with score >= HIGH_SCORE_THRESHOLD."""
    score_pct = int(job.match_score * 100)
    gap = job.gap_analysis or {}
    strong = "\n".join(f"   • {s}" for s in gap.get("strong_matches", [])[:3])
    missing = "\n".join(f"   • {s}" for s in gap.get("missing_skills", [])[:3])

    text = (
        f"🎯 <b>发现匹配岗位！</b>\n\n"
        f"💼 <b>{job.title}</b> @ {job.company}\n"
        f"📍 {job.location}\n"
        f"💰 {job.salary_range or 'N/A'}\n"
        f"🎯 匹配度: {score_pct}%\n"
    )
    if strong:
        text += f"\n✅ 强匹配:\n{strong}\n"
    if missing:
        text += f"\n⚠️ 技能差距:\n{missing}\n"
    if job.source_url:
        text += f"\n👉 <a href='{job.source_url}'>查看详情</a>"

    return _send(text)


def push_daily_summary(stats: dict, high_jobs: list[Job], mid_jobs: list[Job]) -> bool:
    """Daily summary push."""
    from datetime import date
    today = date.today().isoformat()

    seek_count = stats.get("seek", 0)
    linkedin_count = stats.get("linkedin", 0)

    text = (
        f"📊 <b>今日岗位报告 ({today})</b>\n\n"
        f"🔍 爬取统计:\n"
        f"   • Seek: {seek_count} 个新职位\n"
        f"   • LinkedIn: {linkedin_count} 个新职位\n\n"
    )

    if high_jobs:
        text += f"🎯 高分岗位 (≥ 80%): {len(high_jobs)} 个\n"
        for i, j in enumerate(high_jobs[:5], 1):
            text += f"   {i}. {j.company} - {j.title} ({int(j.match_score * 100)}%)\n"
        text += "\n"

    if mid_jobs:
        text += f"📋 中等岗位 (70-80%): {len(mid_jobs)} 个\n"
        for i, j in enumerate(mid_jobs[:5], 1):
            text += f"   {i}. {j.company} - {j.title} ({int(j.match_score * 100)}%)\n"

    return _send(text)
