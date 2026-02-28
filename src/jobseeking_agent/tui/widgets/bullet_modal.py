"""Reusable modal for editing a single Bullet (raw / tech / metric)."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, TextArea


class BulletModal(ModalScreen):
    """Push this screen to create or edit a Bullet.

    Dismisses with a ``dict(raw, tech, metric)`` on Save, or ``None`` on Cancel.
    """

    def __init__(self, bullet: dict | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._bullet = bullet or {}

    def compose(self) -> ComposeResult:
        with Container(id="modal-content"):
            yield Label("[bold]Edit Bullet[/bold]", markup=True)
            yield Label("Achievement text:")
            yield TextArea(self._bullet.get("raw", ""), id="bullet-raw")
            yield Label("Technologies (comma-separated):")
            yield Input(
                ", ".join(self._bullet.get("tech", [])),
                id="bullet-tech",
                placeholder="Python, FastAPI, Docker, ...",
            )
            yield Label("Key metric (optional):")
            yield Input(
                self._bullet.get("metric", ""),
                id="bullet-metric",
                placeholder="e.g. 40% faster, $2M revenue",
            )
            with Horizontal(id="modal-buttons"):
                yield Button("Save", variant="primary", id="btn-modal-save")
                yield Button("Cancel", id="btn-modal-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-modal-save":
            raw = self.query_one("#bullet-raw", TextArea).text.strip()
            if not raw:
                self.app.notify("Achievement text cannot be empty.", severity="warning")
                return
            tech_str = self.query_one("#bullet-tech", Input).value
            tech = [t.strip() for t in tech_str.split(",") if t.strip()]
            metric = self.query_one("#bullet-metric", Input).value.strip()
            self.dismiss({"raw": raw, "tech": tech, "metric": metric})
        else:
            self.dismiss(None)
