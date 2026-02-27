"""
CLI entry point.
Usage:
    python -m jobseeking_agent.cli scout          # 单条 JD 粘贴
    python -m jobseeking_agent.cli batch-scout    # 批量处理 data/jd_inbox/
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


def advisor() -> None:
    from jobseeking_agent.agents.advisor import AdvisorAgent
    from jobseeking_agent.db import get_session, init_db
    from jobseeking_agent.models.application import Application
    from jobseeking_agent.models.job import Job
    from jobseeking_agent.models.user_profile import UserProfile
    from sqlmodel import select

    init_db()

    try:
        profile = UserProfile.load()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)

    with get_session() as session:
        jobs = session.exec(select(Job)).all()
        applications = session.exec(select(Application)).all()

    if not jobs:
        console.print("[yellow]No jobs in DB yet. Run scout first.[/yellow]")
        sys.exit(0)

    console.print(Panel(
        f"[bold]Advisor Agent[/bold] — analysing {len(jobs)} jobs, {len(applications)} applications",
        style="blue",
    ))

    with console.status("[bold green]Generating report...[/bold green]"):
        agent = AdvisorAgent()
        report = agent.run(jobs, applications, profile)

    # Application stats
    stats = report.app_stats
    stats_table = Table(title="Application Stats", show_header=False)
    stats_table.add_column(style="dim")
    stats_table.add_column()
    stats_table.add_row("Jobs analysed", str(report.total_jobs_analysed))
    stats_table.add_row("Applied", str(stats["applied"]))
    stats_table.add_row("Responded", str(stats["responded"]))
    stats_table.add_row("Interviews", str(stats["interviews"]))
    stats_table.add_row("Response rate", stats["response_rate"])
    console.print(stats_table)

    # Skill gap table
    gap_table = Table(title="Top Missing Skills (from JDs)", show_header=True)
    gap_table.add_column("Skill")
    gap_table.add_column("Frequency", justify="right")
    for item in report.top_missing_skills[:10]:
        gap_table.add_row(item["skill"], str(item["count"]))
    console.print(gap_table)

    # In-demand skills user has
    present_table = Table(title="Your Skills in Demand", show_header=True, style="green")
    present_table.add_column("Skill")
    present_table.add_column("Frequency", justify="right")
    for item in report.top_present_skills[:8]:
        present_table.add_row(item["skill"], str(item["count"]))
    console.print(present_table)

    console.print(Panel(report.market_summary, title="Market Summary", style="blue"))
    console.print(Panel(report.skill_gap_analysis, title="Skill Gap Analysis"))

    actions_table = Table(title="Recommended Actions", show_header=False, style="yellow")
    actions_table.add_column()
    for i, action in enumerate(report.recommended_actions, 1):
        actions_table.add_row(f"{i}. {action}")
    console.print(actions_table)

    console.print(f"\n[dim]Report saved to data/reports/[/dim]")


def _run_scraper_batch(scraped_jobs, source: str, profile, init_db_fn, get_session_fn) -> None:
    """Shared logic: feed scraped jobs through ScoutAgent and show summary."""
    from jobseeking_agent.agents.scout import ScoutAgent

    if not scraped_jobs:
        console.print("[yellow]No new jobs found.[/yellow]")
        return

    console.print(f"\nFound [bold]{len(scraped_jobs)}[/bold] new jobs. Analysing...\n")
    agent = ScoutAgent()
    saved = skipped = failed = 0

    for scraped in scraped_jobs:
        try:
            with console.status(f"[green]Scoring: {scraped.title or scraped.url[:60]}[/green]"):
                job = agent.run(
                    raw_jd=scraped.raw_jd,
                    user_profile=profile,
                    source=source,
                    source_url=scraped.url,
                    title=scraped.title,
                    company=scraped.company,
                    location=scraped.location,
                    salary_range=scraped.salary,
                )
            score = job.match_score
            color = "green" if score >= 0.75 else "yellow" if score >= 0.5 else "red"
            console.print(
                f"  [{color}]{score:.0%}[/{color}]  {job.title} @ {job.company}"
            )
            saved += 1
        except Exception as e:
            console.print(f"  [red]Error:[/red] {scraped.url[:60]} — {e}")
            failed += 1

    console.print(
        f"\n[green]Saved: {saved}[/green]  "
        f"[dim]Skipped (dup): {skipped}  Failed: {failed}[/dim]"
    )
    console.print("[dim]Run [bold]cli run[/bold] to review new jobs.[/dim]")


def seek_scout() -> None:
    from jobseeking_agent.db import get_session, init_db
    from jobseeking_agent.models.job import Job
    from jobseeking_agent.models.user_profile import UserProfile
    from jobseeking_agent.scrapers.seek import SeekScraper
    from sqlmodel import select

    init_db()

    try:
        profile = UserProfile.load()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)

    # Load existing URLs for dedup
    with get_session() as session:
        existing_urls = {
            j.source_url for j in session.exec(select(Job)).all() if j.source_url
        }

    console.print(Panel(
        f"[bold]Seek Scout[/bold]\n"
        f"Roles: {', '.join(profile.target_roles)}\n"
        f"Locations: {', '.join(profile.preferences.locations)}\n"
        f"Already in DB: {len(existing_urls)} URLs",
        style="blue",
    ))

    max_per = int(Prompt.ask("Max jobs per role/location query", default="15"))

    with console.status("[bold green]Scraping Seek...[/bold green]"):
        scraper = SeekScraper()
        scraped = scraper.scrape(
            target_roles=profile.target_roles,
            locations=profile.preferences.locations,
            max_per_query=max_per,
            existing_urls=existing_urls,
        )

    _run_scraper_batch(scraped, "seek", profile, init_db, get_session)


def linkedin_scout() -> None:
    from pathlib import Path

    from jobseeking_agent.db import get_session, init_db
    from jobseeking_agent.models.job import Job
    from jobseeking_agent.models.user_profile import UserProfile
    from jobseeking_agent.scrapers.linkedin import URLS_FILE, LinkedInScraper
    from sqlmodel import select

    init_db()

    try:
        profile = UserProfile.load()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)

    if not URLS_FILE.exists():
        URLS_FILE.parent.mkdir(parents=True, exist_ok=True)
        URLS_FILE.write_text(
            "# Paste LinkedIn job URLs here, one per line\n"
            "# Example: https://www.linkedin.com/jobs/view/1234567890\n",
            encoding="utf-8",
        )
        console.print(f"[yellow]Created {URLS_FILE}[/yellow]")
        console.print("Add LinkedIn job URLs (one per line) then re-run this command.")
        sys.exit(0)

    with get_session() as session:
        existing_urls = {
            j.source_url for j in session.exec(select(Job)).all() if j.source_url
        }

    console.print(Panel("[bold]LinkedIn Scout[/bold] — fetching URLs from data/linkedin_urls.txt", style="blue"))

    with console.status("[bold green]Fetching LinkedIn jobs...[/bold green]"):
        scraper = LinkedInScraper()
        scraped = scraper.scrape_from_file(existing_urls=existing_urls)

    _run_scraper_batch(scraped, "linkedin", profile, init_db, get_session)


def run() -> None:
    from jobseeking_agent.db import init_db
    from jobseeking_agent.orchestrator import Orchestrator

    init_db()
    Orchestrator().run()


def schedule() -> None:
    from jobseeking_agent.scheduler import start
    start()


if __name__ == "__main__":
    commands = {
        "scout": scout,
        "seek-scout": seek_scout,
        "linkedin-scout": linkedin_scout,
        "tailor": tailor,
        "apply": apply,
        "advisor": advisor,
        "run": run,
        "schedule": schedule,
    }
    if len(sys.argv) > 1 and sys.argv[1] in commands:
        commands[sys.argv[1]]()
    else:
        console.print(
            "Usage: python -m jobseeking_agent.cli "
            "[scout|seek-scout|linkedin-scout|tailor|apply|advisor|run|schedule]"
        )
