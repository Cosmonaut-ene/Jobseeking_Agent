"""Navigation sidebar widget."""

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Label


class Sidebar(Widget):
    """Left navigation bar with keyboard shortcut hints."""

    class Navigate(Message):
        """Posted when the user clicks a nav button."""

        def __init__(self, target: str) -> None:
            self.target = target
            super().__init__()

    _NAV = [
        ("nav-dashboard", "1  Dashboard",  "dashboard"),
        ("nav-jobs",       "2  Jobs",       "jobs"),
        ("nav-profile",    "3  Profile",    "profile"),
        ("nav-resume",     "4  Resume",     "resume"),
        ("nav-settings",   "5  Settings",   "settings"),
    ]

    def compose(self) -> ComposeResult:
        yield Label("Job Agent", id="sidebar-title")
        for btn_id, label, _ in self._NAV:
            yield Button(label, id=btn_id, classes="nav-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        for btn_id, _, target in self._NAV:
            if event.button.id == btn_id:
                self.post_message(self.Navigate(target))
                break
