"""Resume import wizard — three steps: Upload → Parsing → Review."""

from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widget import Widget
from textual.widgets import Button, ContentSwitcher, Input, Label, LoadingIndicator, Markdown, TextArea


class ResumeScreen(Widget):
    """Three-step wizard: load file ➜ parse with Gemini ➜ review & save."""

    _parsed_profile = None

    def compose(self) -> ComposeResult:
        yield Label("[bold]Resume Import Wizard[/bold]\n", markup=True)
        with ContentSwitcher(initial="step1", id="wizard"):
            # Step 1 ─ upload / paste
            with Container(id="step1"):
                yield Label("[bold]Step 1[/bold]  Load your resume file or paste the text below.", markup=True)
                yield Label("\nFile path (PDF, DOCX, or TXT):")
                yield Input(id="file-path", placeholder="/path/to/resume.pdf")
                yield Button("Load File", id="btn-load-file", variant="primary")
                yield Label("\nOr paste / edit resume text directly:")
                yield TextArea("", id="resume-text")
                yield Button("Parse Resume  →", id="btn-parse", variant="success")

            # Step 2 ─ loading indicator
            with Container(id="step2"):
                yield Label("Parsing with Gemini AI…", id="parsing-label")
                yield LoadingIndicator()

            # Step 3 ─ review result
            with Container(id="step3"):
                yield Label("[bold]Step 3[/bold]  Review the parsed profile.", markup=True)
                yield Markdown("", id="parsed-preview")
                with Horizontal():
                    yield Button("Save as Profile", id="btn-save-profile", variant="success")
                    yield Button("← Back", id="btn-back", variant="default")

    # ── Button handling ─────────────────────────────────────────────────────────

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        wizard = self.query_one("#wizard", ContentSwitcher)

        if btn_id == "btn-load-file":
            self._load_file_to_textarea()

        elif btn_id == "btn-parse":
            text = self.query_one("#resume-text", TextArea).text.strip()
            if not text:
                self.app.notify(
                    "Please load a file or paste resume text first.",
                    severity="warning",
                )
                return
            wizard.current = "step2"
            self._parse_resume(text)

        elif btn_id == "btn-save-profile":
            if not self._parsed_profile:
                self.app.notify("No parsed profile to save.", severity="warning")
                return
            try:
                path = Path("data/user_profile.json")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    self._parsed_profile.model_dump_json(indent=2), encoding="utf-8"
                )
                abs_path = path.resolve()
                self.app.notify(f"Profile saved → {abs_path}")
                # Reset wizard
                wizard.current = "step1"
                self.query_one("#resume-text", TextArea).load_text("")
                self.query_one("#file-path", Input).value = ""
                self._parsed_profile = None
            except Exception as exc:
                self.app.notify(f"Save failed: {exc}", severity="error")

        elif btn_id == "btn-back":
            wizard.current = "step1"

    # ── File loading ─────────────────────────────────────────────────────────────

    def _load_file_to_textarea(self) -> None:
        path_str = self.query_one("#file-path", Input).value.strip()
        if not path_str:
            self.app.notify("Enter a file path first.", severity="warning")
            return
        path = Path(path_str)
        if not path.exists():
            self.app.notify(f"File not found: {path_str}", severity="error")
            return
        try:
            suffix = path.suffix.lower()
            if suffix == ".pdf":
                import pypdf
                reader = pypdf.PdfReader(str(path))
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
            elif suffix in (".docx", ".doc"):
                import docx
                doc = docx.Document(str(path))
                text = "\n".join(p.text for p in doc.paragraphs)
            else:
                text = path.read_text(encoding="utf-8")
            self.query_one("#resume-text", TextArea).load_text(text)
            self.app.notify("File loaded. Review the text, then click 'Parse Resume'.")
        except Exception as exc:
            self.app.notify(f"Error loading file: {exc}", severity="error")

    # ── Gemini parsing (background thread) ──────────────────────────────────────

    @work(thread=True)
    def _parse_resume(self, text: str) -> None:
        from jobseeking_agent.agents.resume_parser import ResumeParserAgent

        try:
            profile = ResumeParserAgent().parse_text(text)
            self._parsed_profile = profile

            # Build preview markdown
            skills_md = "\n".join(
                f"- {s.name} ({s.level}, {s.years}y)" for s in profile.skills
            ) or "_None_"
            exp_md = "\n".join(
                f"- **{e.role}** @ {e.company} ({e.duration})"
                for e in profile.experience
            ) or "_None_"
            proj_md = "\n".join(
                f"- **{p.name}**: {p.description[:80]}{'…' if len(p.description) > 80 else ''}"
                for p in profile.projects
            ) or "_None_"

            md = (
                f"# {profile.name}\n\n"
                f"**Target Roles:** {', '.join(profile.target_roles) or '_None_'}\n\n"
                f"## Skills\n{skills_md}\n\n"
                f"## Experience\n{exp_md}\n\n"
                f"## Projects\n{proj_md}\n\n"
                f"## Preferences\n"
                f"- Locations: {', '.join(profile.preferences.locations) or '_None_'}\n"
                f"- Job Types: {', '.join(profile.preferences.job_types) or '_None_'}\n"
            )

            def _show() -> None:
                self.query_one("#parsed-preview", Markdown).update(md)
                self.query_one("#wizard", ContentSwitcher).current = "step3"

            self.app.call_from_thread(_show)

        except Exception as exc:
            def _err() -> None:
                self.query_one("#wizard", ContentSwitcher).current = "step1"
                self.app.notify(f"Parsing failed: {exc}", severity="error")

            self.app.call_from_thread(_err)
