"""Jobs screen — dual-pane job list with approve/dismiss/tailor/apply actions."""

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, DataTable, Label, LoadingIndicator, Markdown


class JobsScreen(Widget):
    """Left: job list table. Right: detail panel with action buttons."""

    _jobs: list = []
    selected_job_id: reactive[str | None] = reactive(None)

    def compose(self) -> ComposeResult:
        with Vertical(classes="job-list-panel"):
            yield Label("[bold]Jobs[/bold]", markup=True)
            yield DataTable(id="jobs-table")
        with ScrollableContainer(classes="detail-panel"):
            yield Markdown("*Select a job on the left.*", id="job-detail")
            with Horizontal(classes="action-buttons"):
                yield Button("Approve",  id="btn-approve", variant="success",  disabled=True)
                yield Button("Dismiss",  id="btn-dismiss", variant="error",    disabled=True)
                yield Button("Tailor",   id="btn-tailor",  variant="primary",  disabled=True)
                yield Button("Apply",    id="btn-apply",   variant="default",  disabled=True)
            yield LoadingIndicator(id="loading")

    def on_mount(self) -> None:
        loading = self.query_one("#loading", LoadingIndicator)
        loading.display = False

        table = self.query_one("#jobs-table", DataTable)
        table.add_columns("Title", "Company", "Score", "Status")
        table.cursor_type = "row"
        self.load_jobs()

    def on_show(self) -> None:
        self.load_jobs()

    # ── Data loading ────────────────────────────────────────────────────────────

    @work(thread=True)
    def load_jobs(self) -> None:
        from jobseeking_agent.db import get_session
        from jobseeking_agent.models.job import Job
        from sqlmodel import select

        try:
            with get_session() as session:
                jobs = list(session.exec(select(Job).order_by(Job.created_at.desc())).all())
            self.app.call_from_thread(lambda: self._populate_table(jobs))
        except Exception as exc:
            self.app.call_from_thread(
                lambda: self.app.notify(f"Error loading jobs: {exc}", severity="error")
            )

    def _populate_table(self, jobs: list) -> None:
        self._jobs = jobs
        table = self.query_one("#jobs-table", DataTable)
        table.clear()
        for job in jobs:
            table.add_row(
                job.title or "(untitled)",
                job.company or "—",
                f"{job.match_score:.0%}",
                job.status.value,
                key=job.id,
            )

    # ── Row selection ────────────────────────────────────────────────────────────

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        job_id = str(event.row_key.value)
        self.selected_job_id = job_id
        job = next((j for j in self._jobs if j.id == job_id), None)
        if job:
            self._show_detail(job)
            self._set_buttons_disabled(False)

    def _show_detail(self, job) -> None:
        gap = job.gap_analysis or {}
        strong  = "\n".join(f"- {m}" for m in gap.get("strong_matches", []))
        missing = "\n".join(f"- {s}" for s in gap.get("missing_skills", []))
        md = (
            f"## {job.title} @ {job.company}\n\n"
            f"**Status:** {job.status.value}  |  "
            f"**Match:** {job.match_score:.0%}  |  "
            f"**Source:** {job.source}\n\n"
            f"**Location:** {job.location}  |  "
            f"**Salary:** {job.salary_range or 'N/A'}\n\n"
            f"### Strong Matches\n{strong or '_None_'}\n\n"
            f"### Missing Skills\n{missing or '_None_'}\n\n"
            f"### Notes\n{gap.get('notes', '_N/A_')}\n"
        )
        self.query_one("#job-detail", Markdown).update(md)

    def _set_buttons_disabled(self, disabled: bool) -> None:
        for btn_id in ("btn-approve", "btn-dismiss", "btn-tailor", "btn-apply"):
            try:
                self.query_one(f"#{btn_id}", Button).disabled = disabled
            except Exception:
                pass

    def _set_loading(self, loading: bool) -> None:
        try:
            self.query_one("#loading", LoadingIndicator).display = loading
            self._set_buttons_disabled(loading)
        except Exception:
            pass

    # ── Button handlers ──────────────────────────────────────────────────────────

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if not self.selected_job_id:
            return
        btn_id = event.button.id
        if btn_id == "btn-approve":
            self._update_status(self.selected_job_id, "reviewed")
        elif btn_id == "btn-dismiss":
            self._update_status(self.selected_job_id, "dismissed")
        elif btn_id == "btn-tailor":
            self._run_tailor(self.selected_job_id)
        elif btn_id == "btn-apply":
            self._run_apply(self.selected_job_id)

    # ── Workers ──────────────────────────────────────────────────────────────────

    @work(thread=True)
    def _update_status(self, job_id: str, new_status: str) -> None:
        from jobseeking_agent.db import get_session
        from jobseeking_agent.models.job import Job, JobStatus

        try:
            with get_session() as session:
                job = session.get(Job, job_id)
                if job:
                    job.status = JobStatus(new_status)
                    session.add(job)
                    session.commit()

            def _done() -> None:
                self.app.notify(f"Status → '{new_status}'")
                self.load_jobs()

            self.app.call_from_thread(_done)
        except Exception as exc:
            self.app.call_from_thread(
                lambda: self.app.notify(f"Error: {exc}", severity="error")
            )

    @work(thread=True)
    def _run_tailor(self, job_id: str) -> None:
        from jobseeking_agent.agents.tailor import TailorAgent
        from jobseeking_agent.db import get_session
        from jobseeking_agent.models.job import Job
        from jobseeking_agent.models.user_profile import UserProfile

        self.app.call_from_thread(lambda: self._set_loading(True))
        try:
            profile = UserProfile.load()
            with get_session() as session:
                job = session.get(Job, job_id)
            version = TailorAgent().run(job, profile)
            with get_session() as session:
                session.add(version)
                session.commit()

            def _done() -> None:
                self._set_loading(False)
                self.app.notify(f"Resume tailored! ATS: {version.ats_score:.0%}")

            self.app.call_from_thread(_done)
        except Exception as exc:
            def _err() -> None:
                self._set_loading(False)
                self.app.notify(f"Tailor error: {exc}", severity="error")

            self.app.call_from_thread(_err)

    @work(thread=True)
    def _run_apply(self, job_id: str) -> None:
        from jobseeking_agent.agents.applier import ApplierAgent
        from jobseeking_agent.db import get_session
        from jobseeking_agent.models.application import ApplicationChannel
        from jobseeking_agent.models.job import Job, JobStatus
        from jobseeking_agent.models.resume_version import ResumeVersion
        from jobseeking_agent.models.user_profile import UserProfile
        from sqlmodel import select

        self.app.call_from_thread(lambda: self._set_loading(True))
        try:
            profile = UserProfile.load()
            with get_session() as session:
                job = session.get(Job, job_id)
                version = session.exec(
                    select(ResumeVersion)
                    .where(ResumeVersion.job_id == job_id)
                    .order_by(ResumeVersion.created_at.desc())
                ).first()

            if not version:
                def _warn() -> None:
                    self._set_loading(False)
                    self.app.notify("Tailor the resume first!", severity="warning")

                self.app.call_from_thread(_warn)
                return

            application, _ = ApplierAgent().run(
                job, version, profile, ApplicationChannel.manual, ""
            )
            with get_session() as session:
                db_job = session.get(Job, job_id)
                db_job.status = JobStatus.applied
                session.add(db_job)
                session.add(application)
                session.commit()

            def _done() -> None:
                self._set_loading(False)
                self.app.notify("Application recorded!")
                self.load_jobs()

            self.app.call_from_thread(_done)
        except Exception as exc:
            def _err() -> None:
                self._set_loading(False)
                self.app.notify(f"Apply error: {exc}", severity="error")

            self.app.call_from_thread(_err)
