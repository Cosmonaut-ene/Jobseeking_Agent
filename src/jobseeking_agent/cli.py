"""
CLI entry point.
Usage:
    python -m jobseeking_agent.cli scout
    python -m jobseeking_agent.cli tailor
    python -m jobseeking_agent.cli apply
"""

import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

load_dotenv()

console = Console()


def scout() -> None:
    from jobseeking_agent.agents.scout import ScoutAgent
    from jobseeking_agent.db import init_db
    from jobseeking_agent.models.user_profile import UserProfile

    init_db()

    try:
        profile = UserProfile.load()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)

    console.print(Panel("[bold]Scout Agent[/bold] — 粘贴 JD 文本，输入完后另起一行输入 --- 结束", style="blue"))
    console.print("[dim]Paste JD below, then type  ---  on a new line and press Enter:[/dim]\n")

    lines = []
    while True:
        line = input()
        if line.strip() == "---":
            break
        lines.append(line)

    raw_jd = "\n".join(lines).strip()
    if not raw_jd:
        console.print("[red]No input received.[/red]")
        sys.exit(1)

    source = Prompt.ask("Source", choices=["linkedin", "seek", "indeed", "manual"], default="manual")

    with console.status("[bold green]Analyzing JD...[/bold green]"):
        agent = ScoutAgent()
        job = agent.run(raw_jd, profile, source=source)

    _display_scout_result(job)


def tailor() -> None:
    from jobseeking_agent.agents.tailor import TailorAgent
    from jobseeking_agent.db import get_session, init_db
    from jobseeking_agent.models.job import Job, JobStatus
    from jobseeking_agent.models.resume_version import ResumeVersion
    from jobseeking_agent.models.user_profile import UserProfile
    from sqlmodel import select

    init_db()

    try:
        profile = UserProfile.load()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)

    # List jobs available for tailoring
    with get_session() as session:
        jobs = session.exec(
            select(Job).where(Job.status.in_([JobStatus.new, JobStatus.reviewed]))
            .order_by(Job.created_at.desc())
        ).all()

    if not jobs:
        console.print("[yellow]No jobs found with status 'new' or 'reviewed'. Run scout first.[/yellow]")
        sys.exit(0)

    table = Table(title="Available Jobs", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Title")
    table.add_column("Company")
    table.add_column("Match", justify="right")
    table.add_column("Status")
    table.add_column("ID", style="dim")

    for i, job in enumerate(jobs):
        score = job.match_score
        color = "green" if score >= 0.75 else "yellow" if score >= 0.5 else "red"
        table.add_row(
            str(i + 1),
            job.title or "(untitled)",
            job.company or "-",
            f"[{color}]{score:.0%}[/{color}]",
            job.status.value,
            job.id[:8],
        )

    console.print(table)

    choice = Prompt.ask("Select job number", default="1")
    try:
        idx = int(choice) - 1
        selected_job = jobs[idx]
    except (ValueError, IndexError):
        console.print("[red]Invalid selection.[/red]")
        sys.exit(1)

    console.print(f"\nTailoring resume for: [bold]{selected_job.title}[/bold] @ {selected_job.company}\n")

    with console.status("[bold green]Tailoring resume...[/bold green]"):
        agent = TailorAgent()
        version = agent.run(selected_job, profile)

    _display_tailor_diff(version, profile)

    if Confirm.ask("\nSave this resume version?"):
        with get_session() as session:
            session.add(version)
            session.commit()
            session.refresh(version)
        console.print(f"[green]Saved.[/green] Resume version ID: [dim]{version.id}[/dim]")
        console.print(f"ATS coverage: [bold]{version.ats_score:.0%}[/bold]")
    else:
        console.print("[dim]Discarded.[/dim]")


def _display_tailor_diff(version, profile) -> None:
    content = version.content_json

    console.print(Panel(content.get("summary", ""), title="Tailored Summary", style="blue"))

    skills_text = "  ".join(content.get("skills", []))
    console.print(Panel(skills_text, title="Selected Skills (ordered by relevance)", style="cyan"))

    for proj in content.get("projects", []):
        console.print(f"\n[bold]{proj['name']}[/bold]")
        for b in proj.get("bullets", []):
            console.print(f"  [dim]Original:[/dim]  {b['source_raw']}")
            console.print(f"  [green]Rewritten:[/green] {b['rewritten']}")
            console.print()

    ats_color = "green" if version.ats_score >= 0.7 else "yellow" if version.ats_score >= 0.4 else "red"
    console.print(Panel(
        f"ATS coverage: [{ats_color}]{version.ats_score:.0%}[/{ats_color}]\n{version.changes_summary}",
        title="Summary of Changes",
    ))


def _display_scout_result(job) -> None:
    score_color = "green" if job.match_score >= 0.75 else "yellow" if job.match_score >= 0.5 else "red"
    score_str = f"[{score_color}]{job.match_score:.0%}[/{score_color}]"

    console.print()
    console.print(Panel(
        f"[bold]{job.title}[/bold] @ {job.company}\n"
        f"Location: {job.location}   Salary: {job.salary_range or 'N/A'}\n"
        f"Match score: {score_str}",
        title="Job Saved",
        style="bold",
    ))

    gap = job.gap_analysis

    if gap.get("strong_matches"):
        table = Table(title="Strong Matches", style="green", show_header=False)
        table.add_column()
        for item in gap["strong_matches"]:
            table.add_row(f"✓ {item}")
        console.print(table)

    if gap.get("missing_skills"):
        table = Table(title="Skill Gaps", style="red", show_header=False)
        table.add_column()
        for item in gap["missing_skills"]:
            table.add_row(f"✗ {item}")
        console.print(table)

    if gap.get("notes"):
        console.print(Panel(gap["notes"], title="Notes", style="dim"))

    console.print(f"\n[dim]Job ID: {job.id}[/dim]")


def apply() -> None:
    from jobseeking_agent.agents.applier import ApplierAgent
    from jobseeking_agent.db import get_session, init_db
    from jobseeking_agent.models.application import ApplicationChannel
    from jobseeking_agent.models.job import Job, JobStatus
    from jobseeking_agent.models.resume_version import ResumeVersion
    from jobseeking_agent.models.user_profile import UserProfile
    from sqlmodel import select

    init_db()

    try:
        profile = UserProfile.load()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)

    # List jobs that have at least one ResumeVersion
    with get_session() as session:
        versions = session.exec(select(ResumeVersion)).all()
        version_by_job: dict[str, ResumeVersion] = {}
        for v in versions:
            # Keep the most recent version per job
            if v.job_id not in version_by_job or v.created_at > version_by_job[v.job_id].created_at:
                version_by_job[v.job_id] = v

        if not version_by_job:
            console.print("[yellow]No tailored resumes found. Run tailor first.[/yellow]")
            sys.exit(0)

        jobs = session.exec(
            select(Job).where(Job.id.in_(list(version_by_job.keys())))
            .order_by(Job.created_at.desc())
        ).all()

    table = Table(title="Jobs with Tailored Resumes", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Title")
    table.add_column("Company")
    table.add_column("Match", justify="right")
    table.add_column("ATS", justify="right")
    table.add_column("Status")

    for i, job in enumerate(jobs):
        v = version_by_job[job.id]
        score_color = "green" if job.match_score >= 0.75 else "yellow" if job.match_score >= 0.5 else "red"
        ats_color = "green" if v.ats_score >= 0.7 else "yellow" if v.ats_score >= 0.4 else "red"
        table.add_row(
            str(i + 1),
            job.title or "(untitled)",
            job.company or "-",
            f"[{score_color}]{job.match_score:.0%}[/{score_color}]",
            f"[{ats_color}]{v.ats_score:.0%}[/{ats_color}]",
            job.status.value,
        )

    console.print(table)

    choice = Prompt.ask("Select job number", default="1")
    try:
        idx = int(choice) - 1
        selected_job = jobs[idx]
        selected_version = version_by_job[selected_job.id]
    except (ValueError, IndexError):
        console.print("[red]Invalid selection.[/red]")
        sys.exit(1)

    channel_str = Prompt.ask(
        "Channel",
        choices=["email", "easy_apply", "manual"],
        default="email",
    )
    channel = ApplicationChannel(channel_str)
    notes = Prompt.ask("Notes (optional)", default="")

    if channel == ApplicationChannel.manual:
        console.print("[dim]Manual channel — skipping cover letter generation.[/dim]")
    else:
        console.print(f"\n[bold]Generating cover letter for {selected_job.title} @ {selected_job.company}...[/bold]")

    with console.status("[bold green]Working...[/bold green]"):
        agent = ApplierAgent()
        application, cover_path = agent.run(
            selected_job, selected_version, profile, channel, notes
        )

    if cover_path:
        cover_text = open(cover_path, encoding="utf-8").read()
        console.print(Panel(cover_text, title="Cover Letter", style="blue"))
        console.print(f"[dim]Saved to: {cover_path}[/dim]\n")

    if not Confirm.ask("Confirm application and save record?"):
        console.print("[dim]Cancelled.[/dim]")
        sys.exit(0)

    with get_session() as session:
        # Update job status to applied
        job_in_db = session.get(Job, selected_job.id)
        job_in_db.status = JobStatus.applied
        session.add(job_in_db)
        session.add(application)
        session.commit()
        session.refresh(application)

    console.print(f"[green]Application recorded.[/green]")
    console.print(f"Follow-up reminder: [bold]{application.follow_up_date}[/bold]")
    console.print(f"[dim]Application ID: {application.id}[/dim]")


if __name__ == "__main__":
    commands = {"scout": scout, "tailor": tailor, "apply": apply}
    if len(sys.argv) > 1 and sys.argv[1] in commands:
        commands[sys.argv[1]]()
    else:
        console.print("Usage: python -m jobseeking_agent.cli [scout|tailor|apply]")
