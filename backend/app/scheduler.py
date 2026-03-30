"""APScheduler — wraps the daily scout job."""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.app.config import SCHEDULER_HOUR, SCHEDULER_MINUTE, SCHEDULER_ENABLED

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _daily_job() -> None:
    """Runs inside APScheduler background thread."""
    logger.info("[APScheduler] Triggering daily scout job...")
    try:
        from backend.app.scrapers.scheduler import run_daily_scout
        result = run_daily_scout()
        logger.info("[APScheduler] Daily scout done: %s", result)
    except Exception as e:
        logger.error("[APScheduler] Daily scout failed: %s", e)
        try:
            from backend.app.notifications import push_error_notification
            push_error_notification(f"Daily scout failed: {e}")
        except Exception:
            pass  # 通知失败不能影响调度器本身


def start_scheduler() -> None:
    global _scheduler
    if not SCHEDULER_ENABLED:
        logger.info("[APScheduler] Scheduler disabled by config.")
        return
    _scheduler = BackgroundScheduler(timezone="Australia/Sydney")
    _scheduler.add_job(
        _daily_job,
        trigger=CronTrigger(hour=SCHEDULER_HOUR, minute=SCHEDULER_MINUTE),
        id="daily_scout",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("[APScheduler] Scheduler started — daily scout at %02d:%02d AEDT", SCHEDULER_HOUR, SCHEDULER_MINUTE)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        logger.info("[APScheduler] Scheduler stopped.")


def trigger_now() -> None:
    """Manually trigger the daily scout job immediately."""
    _daily_job()
