"""
JobSeekingApp — root Textual application.
Launch with:  python -m jobseeking_agent.cli ui
"""

import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import ContentSwitcher

# ── CSS path: works both in dev and inside a PyInstaller bundle ───────────────
_MEIPASS = getattr(sys, "_MEIPASS", None)
if _MEIPASS:
    _CSS_PATH = Path(_MEIPASS) / "jobseeking_agent" / "tui" / "app.tcss"
else:
    _CSS_PATH = Path(__file__).parent / "app.tcss"


class JobSeekingApp(App):
    CSS_PATH = str(_CSS_PATH)

    BINDINGS = [
        Binding("1", "show_dashboard", "Dashboard"),
        Binding("2", "show_jobs", "Jobs"),
        Binding("3", "show_profile", "Profile"),
        Binding("4", "show_resume", "Resume"),
        Binding("5", "show_settings", "Settings"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        from jobseeking_agent.tui.screens.dashboard import DashboardScreen
        from jobseeking_agent.tui.screens.jobs import JobsScreen
        from jobseeking_agent.tui.screens.profile import ProfileScreen
        from jobseeking_agent.tui.screens.resume import ResumeScreen
        from jobseeking_agent.tui.screens.settings import SettingsScreen
        from jobseeking_agent.tui.widgets.sidebar import Sidebar

        yield Sidebar()
        yield ContentSwitcher(
            DashboardScreen(id="dashboard"),
            JobsScreen(id="jobs"),
            ProfileScreen(id="profile"),
            ResumeScreen(id="resume"),
            SettingsScreen(id="settings"),
            initial="dashboard",
        )

    def on_mount(self) -> None:
        import os
        from jobseeking_agent.db import init_db
        init_db()
        # If no API key is configured, redirect to Settings immediately
        if not os.environ.get("GEMINI_API_KEY"):
            self.query_one(ContentSwitcher).current = "settings"
            self.notify(
                "No API key found — please enter your Gemini API key.",
                severity="warning",
                timeout=6,
            )

    # ── Sidebar navigation message ─────────────────────────────────────────────
    def on_sidebar_navigate(self, message) -> None:
        self.query_one(ContentSwitcher).current = message.target

    # ── Keyboard actions ───────────────────────────────────────────────────────
    def action_show_dashboard(self) -> None:
        self.query_one(ContentSwitcher).current = "dashboard"

    def action_show_jobs(self) -> None:
        self.query_one(ContentSwitcher).current = "jobs"

    def action_show_profile(self) -> None:
        self.query_one(ContentSwitcher).current = "profile"

    def action_show_resume(self) -> None:
        self.query_one(ContentSwitcher).current = "resume"

    def action_show_settings(self) -> None:
        self.query_one(ContentSwitcher).current = "settings"
