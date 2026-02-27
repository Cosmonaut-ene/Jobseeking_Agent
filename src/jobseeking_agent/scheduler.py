"""
Scheduler — 后台定时任务。

任务：
  - 每周一 09:00 自动运行 Advisor Agent，报告保存到 data/reports/
"""

from apscheduler.schedulers.blocking import BlockingScheduler
from rich.console import Console

console = Console()


def _run_advisor() -> None:
    from dotenv import load_dotenv
    from sqlmodel import select

    from jobseeking_agent.agents.advisor import AdvisorAgent
    from jobseeking_agent.db import get_session, init_db
    from jobseeking_agent.models.application import Application
    from jobseeking_agent.models.job import Job
    from jobseeking_agent.models.user_profile import UserProfile

    load_dotenv()
    init_db()

    try:
        profile = UserProfile.load()
    except FileNotFoundError as e:
        console.print(f"[red][Scheduler] {e}[/red]")
        return

    with get_session() as session:
        jobs = session.exec(select(Job)).all()
        applications = session.exec(select(Application)).all()

    if not jobs:
        console.print("[dim][Scheduler] No jobs in DB, skipping Advisor.[/dim]")
        return

    console.print("[bold green][Scheduler] Running weekly Advisor...[/bold green]")
    agent = AdvisorAgent()
    report = agent.run(jobs, applications, profile)
    console.print(f"[green][Scheduler] Advisor report saved. ATS summary: {len(report.recommended_actions)} actions.[/green]")


def start() -> None:
    scheduler = BlockingScheduler(timezone="Australia/Sydney")

    # Weekly Advisor — every Monday at 09:00
    scheduler.add_job(
        _run_advisor,
        trigger="cron",
        day_of_week="mon",
        hour=9,
        minute=0,
        id="weekly_advisor",
        name="Weekly Advisor Report",
    )

    console.print("[bold blue]Scheduler started.[/bold blue]")
    console.print("  [dim]Weekly Advisor: every Monday 09:00 (Australia/Sydney)[/dim]")
    console.print("  [dim]Press Ctrl+C to stop.[/dim]\n")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        console.print("\n[dim]Scheduler stopped.[/dim]")
