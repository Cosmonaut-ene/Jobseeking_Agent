"""Settings screen — API key and other runtime configuration."""

import os
import sys
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Static


def _env_path() -> Path:
    if getattr(sys, "frozen", False):
        # exe 在 dist/ 里，上一级就是项目根目录
        return Path(sys.executable).parent.parent / ".env"
    # 开发模式：CWD 即项目根目录
    return Path(".env")


def _load_env_dict() -> dict[str, str]:
    """Parse .env file into a plain dict (keeps existing keys intact)."""
    result: dict[str, str] = {}
    if _env_path().exists():
        for line in _env_path().read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                result[k.strip()] = v.strip()
    return result


def _save_env_dict(data: dict[str, str]) -> Path:
    """Write dict back to .env, preserving comment lines. Returns the path written."""
    p = _env_path()
    lines: list[str] = []
    if p.exists():
        existing = p.read_text(encoding="utf-8").splitlines()
        written: set[str] = set()
        for line in existing:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k = stripped.partition("=")[0].strip()
                if k in data:
                    lines.append(f"{k}={data[k]}")
                    written.add(k)
                else:
                    lines.append(line)
            else:
                lines.append(line)
        for k, v in data.items():
            if k not in written:
                lines.append(f"{k}={v}")
    else:
        for k, v in data.items():
            lines.append(f"{k}={v}")

    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


class SettingsScreen(Widget):
    """Edit runtime settings (API keys, etc.) and save to .env."""

    def compose(self) -> ComposeResult:
        yield Label("[bold]Settings[/bold]\n", markup=True)

        yield Static(
            "The API key is saved to [bold].env[/bold] in the working directory "
            "and loaded automatically on next launch.",
            markup=True,
        )

        yield Label("\nGemini API Key:", classes="settings-label")
        with Horizontal(classes="settings-row"):
            yield Input(
                password=True,
                placeholder="AIza...",
                id="input-gemini-key",
            )
            yield Button("Show", id="btn-toggle-key", variant="default")

        yield Label("", id="key-status")

        yield Button("Save", id="btn-save-settings", variant="success")

    # ── Lifecycle ────────────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        self._refresh_fields()

    def on_show(self) -> None:
        self._refresh_fields()

    def _refresh_fields(self) -> None:
        env = _load_env_dict()
        key = env.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
        inp = self.query_one("#input-gemini-key", Input)
        inp.value = key
        self._update_status(key)

    def _update_status(self, key: str) -> None:
        label = self.query_one("#key-status", Label)
        if key:
            label.update("[green]✓ API key is set[/green]")
        else:
            label.update("[red]✗ API key is missing — the app cannot call Gemini[/red]")

    # ── Button handlers ──────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        if btn_id == "btn-toggle-key":
            inp = self.query_one("#input-gemini-key", Input)
            inp.password = not inp.password
            event.button.label = "Hide" if not inp.password else "Show"

        elif btn_id == "btn-save-settings":
            self._save()

    def _save(self) -> None:
        key = self.query_one("#input-gemini-key", Input).value.strip()
        if not key:
            self.app.notify("API key cannot be empty.", severity="warning")
            return

        # Inject into current process immediately so agents work without restart
        os.environ["GEMINI_API_KEY"] = key
        self._update_status(key)

        # Persist to .env (show exact path so the user knows where it went)
        try:
            env = _load_env_dict()
            env["GEMINI_API_KEY"] = key
            saved_path = _save_env_dict(env)
            self.app.notify(f"Saved → {saved_path.resolve()}")
        except Exception as exc:
            self.app.notify(
                f"Key is active this session but .env write failed: {exc}",
                severity="warning",
            )
