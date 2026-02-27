"""
CLI entry point.
Usage:
    python -m jobseeking_agent.cli scout
"""

import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

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

    _display_result(job)


def _display_result(job) -> None:
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


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "scout":
        scout()
    else:
        console.print("Usage: python -m jobseeking_agent.cli scout")
