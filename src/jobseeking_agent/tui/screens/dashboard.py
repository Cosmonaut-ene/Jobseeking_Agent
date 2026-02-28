"""Dashboard screen — job-pipeline stats + follow-up table."""

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import DataTable, Label


_STATUSES = ["new", "reviewed", "applied", "interview", "offer"]


class DashboardScreen(Widget):
    """Overview of the hiring pipeline."""

    def compose(self) -> ComposeResult:
        yield Label("[bold]Dashboard[/bold]\n", markup=True)
        with Horizontal(id="stats-row"):
            for name in _STATUSES:
                with Vertical(classes="stat-box"):
                    yield Label("—", id=f"stat-{name}", classes="stat-count")
                    yield Label(name.capitalize(), classes="stat-label")
        yield Label("\n[bold]Follow-up Required[/bold]", markup=True)
        yield DataTable(id="followup-table")

    def on_mount(self) -> None:
        table = self.query_one("#followup-table", DataTable)
        table.add_columns("Title", "Company", "Status", "Last Updated")

    def on_show(self) -> None:
        self.load_data()

    @work(thread=True)
    def load_data(self) -> None:
        from jobseeking_agent.db import get_session
        from jobseeking_agent.models.job import Job
        from sqlmodel import select

        try:
            with get_session() as session:
                jobs = list(session.exec(select(Job)).all())

            counts = {s: 0 for s in _STATUSES}
            followups: list[tuple] = []
            for job in jobs:
                s = job.status.value
                if s in counts:
                    counts[s] += 1
                if s in ("applied", "interview"):
                    followups.append((
                        job.title or "(untitled)",
                        job.company or "—",
                        s,
                        str(job.updated_at.date()),
                    ))

            def _update() -> None:
                for name, count in counts.items():
                    try:
                        self.query_one(f"#stat-{name}", Label).update(str(count))
                    except Exception:
                        pass
                try:
                    table = self.query_one("#followup-table", DataTable)
                    table.clear()
                    for row in followups:
                        table.add_row(*row)
                except Exception:
                    pass

            self.app.call_from_thread(_update)

        except Exception as exc:
            self.app.call_from_thread(
                lambda: self.app.notify(f"Dashboard error: {exc}", severity="error")
            )
