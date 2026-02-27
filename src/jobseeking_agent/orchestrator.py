"""
Orchestrator — 管道仪表盘 + 人工审核门控。

职责：
  1. 展示各阶段 job 数量（仪表盘）
  2. 逐个 review `new` 状态的 job → approved(reviewed) / dismissed
  3. 展示到期 follow-up 提醒

Tailor / Apply 仍保留独立 CLI 命令，由用户手动触发。
"""

from datetime import date

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from jobseeking_agent.db import get_session
from jobseeking_agent.models.application import Application
from jobseeking_agent.models.job import Job, JobStatus
from jobseeking_agent.models.resume_version import ResumeVersion

console = Console()

# Status display config: (label, color)
STATUS_META: dict[str, tuple[str, str]] = {
    JobStatus.new:       ("New",       "yellow"),
    JobStatus.reviewed:  ("Reviewed",  "cyan"),
    JobStatus.dismissed: ("Dismissed", "dim"),
    JobStatus.applied:   ("Applied",   "blue"),
    JobStatus.interview: ("Interview", "green"),
    JobStatus.rejected:  ("Rejected",  "red"),
    JobStatus.offer:     ("Offer",     "bold green"),
}


class Orchestrator:
    def run(self) -> None:
        with get_session() as session:
            from sqlmodel import select
            jobs = session.exec(select(Job)).all()
            applications = session.exec(select(Application)).all()
            versions = session.exec(select(ResumeVersion)).all()

        self._show_pipeline(jobs, applications, versions)
        self._review_new_jobs(jobs)
        self._show_followup_reminders(applications, jobs)

    # ── Pipeline dashboard ────────────────────────────────────────────────────

    def _show_pipeline(
        self,
        jobs: list[Job],
        applications: list[Application],
        versions: list[ResumeVersion],
    ) -> None:
        versioned_job_ids = {v.job_id for v in versions}

        table = Table(title="Pipeline Status", show_header=True, show_lines=False)
        table.add_column("Stage")
        table.add_column("Count", justify="right")
        table.add_column("Jobs", style="dim")

        stage_data = [
            (JobStatus.new,       "Pending review"),
            (JobStatus.reviewed,  "Ready to tailor / apply"),
            (JobStatus.applied,   "Tracking"),
            (JobStatus.interview, "In interview"),
            (JobStatus.offer,     "Offer received"),
            (JobStatus.rejected,  "Closed (rejected)"),
            (JobStatus.dismissed, "Dismissed"),
        ]

        for status, hint in stage_data:
            group = [j for j in jobs if j.status == status]
            label, color = STATUS_META[status]
            names = ", ".join(
                f"{j.company}/{j.title[:20]}" for j in group[:3]
            )
            if len(group) > 3:
                names += f" +{len(group) - 3} more"
            table.add_row(
                f"[{color}]{label}[/{color}]",
                f"[{color}]{len(group)}[/{color}]",
                names or "-",
            )

        # Extra: reviewed jobs with tailored resume ready to apply
        ready = [j for j in jobs if j.status == JobStatus.reviewed and j.id in versioned_job_ids]
        if ready:
            names = ", ".join(f"{j.company}/{j.title[:20]}" for j in ready[:3])
            table.add_row("[cyan]  └ tailored, awaiting apply[/cyan]", f"[cyan]{len(ready)}[/cyan]", names)

        console.print(table)

        # Summary line
        active = sum(1 for j in jobs if j.status not in (JobStatus.dismissed, JobStatus.rejected))
        console.print(f"[dim]Total: {len(jobs)} jobs  |  Active: {active}  |  Applications: {len(applications)}[/dim]\n")

    # ── Review new jobs ───────────────────────────────────────────────────────

    def _review_new_jobs(self, jobs: list[Job]) -> None:
        new_jobs = [j for j in jobs if j.status == JobStatus.new]
        if not new_jobs:
            console.print("[dim]No new jobs to review.[/dim]\n")
            return

        console.print(f"[bold yellow]{len(new_jobs)} new job(s) to review.[/bold yellow]")
        console.print("[dim]For each job: [A]pprove → reviewed  |  [D]ismiss  |  [S]kip[/dim]\n")

        approved = dismissed = skipped = 0

        with get_session() as session:
            for job in new_jobs:
                score = job.match_score
                color = "green" if score >= 0.75 else "yellow" if score >= 0.5 else "red"
                gap = job.gap_analysis

                console.print(Panel(
                    f"[bold]{job.title}[/bold] @ {job.company}\n"
                    f"Location: {job.location or 'N/A'}   "
                    f"Match: [{color}]{score:.0%}[/{color}]\n"
                    f"Strong: {', '.join(gap.get('strong_matches', [])) or 'N/A'}\n"
                    f"Missing: {', '.join(gap.get('missing_skills', [])) or 'none'}\n"
                    f"[dim]{gap.get('notes', '')}[/dim]",
                    title=f"[yellow]Review[/yellow] — {job.source}",
                ))

                choice = Prompt.ask("Action", choices=["a", "d", "s"], default="s").lower()

                job_in_db = session.get(Job, job.id)
                if choice == "a":
                    job_in_db.status = JobStatus.reviewed
                    session.add(job_in_db)
                    approved += 1
                elif choice == "d":
                    job_in_db.status = JobStatus.dismissed
                    session.add(job_in_db)
                    dismissed += 1
                else:
                    skipped += 1

            session.commit()

        console.print(
            f"\nReview complete — "
            f"[green]approved: {approved}[/green]  "
            f"[red]dismissed: {dismissed}[/red]  "
            f"[dim]skipped: {skipped}[/dim]\n"
        )
        if approved:
            console.print("[dim]Run [bold]tailor[/bold] to generate tailored resumes for approved jobs.[/dim]")

    # ── Follow-up reminders ───────────────────────────────────────────────────

    def _show_followup_reminders(
        self, applications: list[Application], jobs: list[Job]
    ) -> None:
        today = date.today()
        due = [a for a in applications if a.follow_up_date and a.follow_up_date <= today]
        if not due:
            console.print("[dim]No follow-ups due.[/dim]")
            return

        job_map = {j.id: j for j in jobs}
        table = Table(title=f"Follow-ups Due ({len(due)})", style="yellow", show_lines=True)
        table.add_column("Company")
        table.add_column("Role")
        table.add_column("Due Date")
        table.add_column("Channel")
        table.add_column("App ID", style="dim")

        for app in due:
            job = job_map.get(app.job_id)
            overdue = (today - app.follow_up_date).days
            date_str = str(app.follow_up_date)
            if overdue > 0:
                date_str = f"[red]{date_str} ({overdue}d overdue)[/red]"
            table.add_row(
                job.company if job else "?",
                job.title if job else "?",
                date_str,
                app.channel.value,
                app.id[:8],
            )

        console.print(table)
