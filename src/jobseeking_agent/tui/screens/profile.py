"""UserProfile editor — TabbedContent with Skills / Experience / Projects / Preferences."""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import (
    Button,
    Input,
    Label,
    ListItem,
    ListView,
    TabbedContent,
    TabPane,
    TextArea,
)


class ProfileScreen(Widget):
    """In-memory UserProfile editor. Persists on 'Save to File'."""

    _profile_path = Path("data/user_profile.json")
    _profile = None

    # Track selected indices for list panels
    _sel_skill: int | None = None
    _sel_exp:   int | None = None
    _sel_proj:  int | None = None

    # ── Layout ──────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        with Horizontal(id="profile-header"):
            yield Label("[bold]User Profile[/bold]", markup=True)
            yield Button("Save to File", id="btn-save", variant="success")

        with TabbedContent(initial="tab-basic"):

            # ── Basic ──────────────────────────────────────────────────────────
            with TabPane("Basic", id="tab-basic"):
                yield Label("Name:")
                yield Input(id="profile-name", placeholder="Your full name")
                yield Label("Target Roles (one per line):")
                yield TextArea("", id="profile-roles")

            # ── Skills ─────────────────────────────────────────────────────────
            with TabPane("Skills", id="tab-skills"):
                with Horizontal():
                    with Vertical(classes="list-col"):
                        yield Label("Skills")
                        yield ListView(id="skills-list")
                    with Vertical(classes="form-col"):
                        yield Label("Skill Name:")
                        yield Input(id="skill-name", placeholder="e.g. Python")
                        yield Label("Level (beginner / intermediate / expert):")
                        yield Input(id="skill-level", placeholder="intermediate")
                        yield Label("Years of experience:")
                        yield Input(id="skill-years", placeholder="0.0")
                        with Horizontal():
                            yield Button("Add",    id="btn-add-skill",    variant="success")
                            yield Button("Update", id="btn-update-skill", variant="primary")
                            yield Button("Delete", id="btn-del-skill",    variant="error")

            # ── Experience ─────────────────────────────────────────────────────
            with TabPane("Experience", id="tab-exp"):
                with Horizontal():
                    with Vertical(classes="list-col"):
                        yield Label("Experience entries")
                        yield ListView(id="exp-list")
                        with Horizontal():
                            yield Button("+ Add",  id="btn-add-exp", variant="success")
                            yield Button("- Del",  id="btn-del-exp", variant="error")
                    with Vertical(classes="form-col"):
                        yield Label("Company:")
                        yield Input(id="exp-company")
                        yield Label("Role / Title:")
                        yield Input(id="exp-role")
                        yield Label("Duration (YYYY-MM ~ YYYY-MM):")
                        yield Input(id="exp-duration", placeholder="2022-01 ~ present")
                        yield Label("Bullets:")
                        yield ListView(id="bullets-exp-list")
                        with Horizontal():
                            yield Button("+ Bullet", id="btn-add-exp-bullet",  variant="success")
                            yield Button("Edit",     id="btn-edit-exp-bullet", variant="primary")
                            yield Button("- Bullet", id="btn-del-exp-bullet",  variant="error")

            # ── Projects ───────────────────────────────────────────────────────
            with TabPane("Projects", id="tab-proj"):
                with Horizontal():
                    with Vertical(classes="list-col"):
                        yield Label("Projects")
                        yield ListView(id="proj-list")
                        with Horizontal():
                            yield Button("+ Add", id="btn-add-proj", variant="success")
                            yield Button("- Del", id="btn-del-proj", variant="error")
                    with Vertical(classes="form-col"):
                        yield Label("Project Name:")
                        yield Input(id="proj-name")
                        yield Label("Description:")
                        yield TextArea("", id="proj-description")
                        yield Label("Tech Stack (comma-separated):")
                        yield Input(id="proj-tech", placeholder="Python, FastAPI, ...")
                        yield Label("Bullets:")
                        yield ListView(id="bullets-proj-list")
                        with Horizontal():
                            yield Button("+ Bullet", id="btn-add-proj-bullet",  variant="success")
                            yield Button("Edit",     id="btn-edit-proj-bullet", variant="primary")
                            yield Button("- Bullet", id="btn-del-proj-bullet",  variant="error")

            # ── Preferences ────────────────────────────────────────────────────
            with TabPane("Preferences", id="tab-prefs"):
                yield Label("Preferred Locations (one per line):")
                yield TextArea("", id="pref-locations")
                yield Label("Job Types (comma-separated, e.g. full-time, contract):")
                yield Input(id="pref-job-types")
                yield Label("Salary Min:")
                yield Input(id="pref-salary-min", placeholder="0")
                yield Label("Salary Max:")
                yield Input(id="pref-salary-max", placeholder="0")
                yield Label("Currency:")
                yield Input(id="pref-currency", placeholder="AUD")

    # ── Lifecycle ───────────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        self._load_profile()

    def on_show(self) -> None:
        # Re-render lists in case another screen modified the file
        if self._profile is not None:
            self._refresh_ui()

    # ── Profile I/O ─────────────────────────────────────────────────────────────

    def _load_profile(self) -> None:
        from jobseeking_agent.models.user_profile import Preferences, UserProfile

        try:
            self._profile = UserProfile.load(self._profile_path)
        except FileNotFoundError:
            self._profile = UserProfile(
                name="",
                target_roles=[],
                skills=[],
                experience=[],
                projects=[],
                preferences=Preferences(locations=[], job_types=[]),
            )
        self._refresh_ui()

    def _refresh_ui(self) -> None:
        p = self._profile
        if p is None:
            return
        try:
            self.query_one("#profile-name", Input).value = p.name
            self.query_one("#profile-roles", TextArea).load_text("\n".join(p.target_roles))
        except Exception:
            pass

        self._refresh_skills_list()
        self._refresh_exp_list()
        self._refresh_proj_list()

        try:
            prefs = p.preferences
            self.query_one("#pref-locations", TextArea).load_text(
                "\n".join(prefs.locations)
            )
            self.query_one("#pref-job-types", Input).value = ", ".join(prefs.job_types)
            if prefs.salary_range:
                self.query_one("#pref-salary-min", Input).value = str(prefs.salary_range.min)
                self.query_one("#pref-salary-max", Input).value = str(prefs.salary_range.max)
                self.query_one("#pref-currency", Input).value = prefs.salary_range.currency
        except Exception:
            pass

    # ── List refresh helpers ─────────────────────────────────────────────────────

    def _refresh_skills_list(self) -> None:
        try:
            lv = self.query_one("#skills-list", ListView)
            lv.clear()
            if self._profile:
                for s in self._profile.skills:
                    lv.append(ListItem(Label(f"{s.name} ({s.level}, {s.years}y)")))
        except Exception:
            pass

    def _refresh_exp_list(self) -> None:
        try:
            lv = self.query_one("#exp-list", ListView)
            lv.clear()
            if self._profile:
                for e in self._profile.experience:
                    lv.append(ListItem(Label(f"{e.role} @ {e.company}")))
        except Exception:
            pass

    def _refresh_exp_bullets(self) -> None:
        try:
            lv = self.query_one("#bullets-exp-list", ListView)
            lv.clear()
            if self._sel_exp is not None and self._profile:
                exp = self._profile.experience[self._sel_exp]
                for b in exp.bullets:
                    lv.append(ListItem(Label(
                        b.raw[:70] + ("…" if len(b.raw) > 70 else "")
                    )))
        except Exception:
            pass

    def _refresh_proj_list(self) -> None:
        try:
            lv = self.query_one("#proj-list", ListView)
            lv.clear()
            if self._profile:
                for p in self._profile.projects:
                    lv.append(ListItem(Label(p.name)))
        except Exception:
            pass

    def _refresh_proj_bullets(self) -> None:
        try:
            lv = self.query_one("#bullets-proj-list", ListView)
            lv.clear()
            if self._sel_proj is not None and self._profile:
                proj = self._profile.projects[self._sel_proj]
                for b in proj.bullets:
                    lv.append(ListItem(Label(
                        b.raw[:70] + ("…" if len(b.raw) > 70 else "")
                    )))
        except Exception:
            pass

    # ── ListView selection ───────────────────────────────────────────────────────

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        lv_id = event.list_view.id
        idx = event.list_view.index

        if lv_id == "skills-list":
            self._sel_skill = idx
            if idx is not None and self._profile and idx < len(self._profile.skills):
                s = self._profile.skills[idx]
                try:
                    self.query_one("#skill-name", Input).value = s.name
                    self.query_one("#skill-level", Input).value = s.level
                    self.query_one("#skill-years", Input).value = str(s.years)
                except Exception:
                    pass

        elif lv_id == "exp-list":
            # Flush current form before switching
            self._collect_current_exp()
            self._sel_exp = idx
            if idx is not None and self._profile and idx < len(self._profile.experience):
                e = self._profile.experience[idx]
                try:
                    self.query_one("#exp-company", Input).value = e.company
                    self.query_one("#exp-role", Input).value = e.role
                    self.query_one("#exp-duration", Input).value = e.duration
                except Exception:
                    pass
                self._refresh_exp_bullets()

        elif lv_id == "proj-list":
            self._collect_current_project()
            self._sel_proj = idx
            if idx is not None and self._profile and idx < len(self._profile.projects):
                p = self._profile.projects[idx]
                try:
                    self.query_one("#proj-name", Input).value = p.name
                    self.query_one("#proj-description", TextArea).load_text(p.description)
                    self.query_one("#proj-tech", Input).value = ", ".join(p.tech_stack)
                except Exception:
                    pass
                self._refresh_proj_bullets()

    # ── Form → profile collectors ─────────────────────────────────────────────────

    def _collect_basic(self) -> None:
        if not self._profile:
            return
        try:
            self._profile.name = self.query_one("#profile-name", Input).value.strip()
            text = self.query_one("#profile-roles", TextArea).text
            self._profile.target_roles = [r.strip() for r in text.splitlines() if r.strip()]
        except Exception:
            pass

    def _collect_prefs(self) -> None:
        if not self._profile:
            return
        from jobseeking_agent.models.user_profile import Preferences, SalaryRange
        try:
            locs_text = self.query_one("#pref-locations", TextArea).text
            locs = [l.strip() for l in locs_text.splitlines() if l.strip()]
            jt_str = self.query_one("#pref-job-types", Input).value
            job_types = [t.strip() for t in jt_str.split(",") if t.strip()]
            try:
                s_min = int(self.query_one("#pref-salary-min", Input).value or "0")
                s_max = int(self.query_one("#pref-salary-max", Input).value or "0")
                currency = self.query_one("#pref-currency", Input).value.strip() or "AUD"
                salary = SalaryRange(min=s_min, max=s_max, currency=currency) if (s_min or s_max) else None
            except ValueError:
                salary = None
            self._profile.preferences = Preferences(
                locations=locs, salary_range=salary, job_types=job_types
            )
        except Exception:
            pass

    def _collect_current_exp(self) -> None:
        if self._sel_exp is None or not self._profile:
            return
        idx = self._sel_exp
        if 0 <= idx < len(self._profile.experience):
            exp = self._profile.experience[idx]
            try:
                exp.company  = self.query_one("#exp-company", Input).value.strip()
                exp.role     = self.query_one("#exp-role", Input).value.strip()
                exp.duration = self.query_one("#exp-duration", Input).value.strip()
            except Exception:
                pass

    def _collect_current_project(self) -> None:
        if self._sel_proj is None or not self._profile:
            return
        idx = self._sel_proj
        if 0 <= idx < len(self._profile.projects):
            proj = self._profile.projects[idx]
            try:
                proj.name        = self.query_one("#proj-name", Input).value.strip()
                proj.description = self.query_one("#proj-description", TextArea).text
                tech_str         = self.query_one("#proj-tech", Input).value
                proj.tech_stack  = [t.strip() for t in tech_str.split(",") if t.strip()]
            except Exception:
                pass

    # ── Save ─────────────────────────────────────────────────────────────────────

    def _save_profile(self) -> None:
        if not self._profile:
            return
        self._collect_basic()
        self._collect_current_exp()
        self._collect_current_project()
        self._collect_prefs()
        self._profile_path.parent.mkdir(parents=True, exist_ok=True)
        self._profile_path.write_text(
            self._profile.model_dump_json(indent=2), encoding="utf-8"
        )
        self.app.notify("Profile saved!")

    # ── Skill CRUD ────────────────────────────────────────────────────────────────

    def _add_skill(self) -> None:
        from jobseeking_agent.models.user_profile import Skill
        try:
            name  = self.query_one("#skill-name", Input).value.strip()
            level = self.query_one("#skill-level", Input).value.strip() or "beginner"
            years = float(self.query_one("#skill-years", Input).value or "0")
        except (ValueError, Exception):
            self.app.notify("Invalid skill fields.", severity="warning")
            return
        if name and self._profile:
            self._profile.skills.append(Skill(name=name, level=level, years=years))
            self._refresh_skills_list()
            self.app.notify(f"Added skill: {name}")

    def _update_skill(self) -> None:
        if self._sel_skill is None or not self._profile:
            return
        from jobseeking_agent.models.user_profile import Skill
        idx = self._sel_skill
        if 0 <= idx < len(self._profile.skills):
            try:
                name  = self.query_one("#skill-name", Input).value.strip()
                level = self.query_one("#skill-level", Input).value.strip() or "beginner"
                years = float(self.query_one("#skill-years", Input).value or "0")
            except (ValueError, Exception):
                return
            self._profile.skills[idx] = Skill(name=name, level=level, years=years)
            self._refresh_skills_list()

    def _delete_skill(self) -> None:
        if self._sel_skill is None or not self._profile:
            return
        idx = self._sel_skill
        if 0 <= idx < len(self._profile.skills):
            name = self._profile.skills[idx].name
            self._profile.skills.pop(idx)
            self._sel_skill = None
            self._refresh_skills_list()
            self.app.notify(f"Deleted skill: {name}")

    # ── Experience CRUD ───────────────────────────────────────────────────────────

    def _add_experience(self) -> None:
        from jobseeking_agent.models.user_profile import Experience
        if self._profile:
            self._profile.experience.append(
                Experience(company="New Company", role="New Role", duration="")
            )
            self._refresh_exp_list()

    def _delete_experience(self) -> None:
        if self._sel_exp is None or not self._profile:
            return
        idx = self._sel_exp
        if 0 <= idx < len(self._profile.experience):
            self._profile.experience.pop(idx)
            self._sel_exp = None
            self._refresh_exp_list()
            self._refresh_exp_bullets()

    async def _edit_exp_bullet(self, is_add: bool) -> None:
        from jobseeking_agent.tui.widgets.bullet_modal import BulletModal

        if self._sel_exp is None or not self._profile:
            return
        exp = self._profile.experience[self._sel_exp]
        bullet_lv = self.query_one("#bullets-exp-list", ListView)
        b_idx = bullet_lv.index

        existing = None
        if not is_add and b_idx is not None and 0 <= b_idx < len(exp.bullets):
            b = exp.bullets[b_idx]
            existing = {"raw": b.raw, "tech": b.tech, "metric": b.metric}

        result = await self.app.push_screen_wait(BulletModal(bullet=existing))
        if result:
            from jobseeking_agent.models.user_profile import Bullet
            new_bullet = Bullet(**result)
            if is_add:
                exp.bullets.append(new_bullet)
            elif b_idx is not None and 0 <= b_idx < len(exp.bullets):
                exp.bullets[b_idx] = new_bullet
            self._refresh_exp_bullets()

    def _delete_exp_bullet(self) -> None:
        if self._sel_exp is None or not self._profile:
            return
        exp = self._profile.experience[self._sel_exp]
        b_idx = self.query_one("#bullets-exp-list", ListView).index
        if b_idx is not None and 0 <= b_idx < len(exp.bullets):
            exp.bullets.pop(b_idx)
            self._refresh_exp_bullets()

    # ── Project CRUD ──────────────────────────────────────────────────────────────

    def _add_project(self) -> None:
        from jobseeking_agent.models.user_profile import Project
        if self._profile:
            self._profile.projects.append(Project(name="New Project", description=""))
            self._refresh_proj_list()

    def _delete_project(self) -> None:
        if self._sel_proj is None or not self._profile:
            return
        idx = self._sel_proj
        if 0 <= idx < len(self._profile.projects):
            self._profile.projects.pop(idx)
            self._sel_proj = None
            self._refresh_proj_list()
            self._refresh_proj_bullets()

    async def _edit_proj_bullet(self, is_add: bool) -> None:
        from jobseeking_agent.tui.widgets.bullet_modal import BulletModal

        if self._sel_proj is None or not self._profile:
            return
        proj = self._profile.projects[self._sel_proj]
        bullet_lv = self.query_one("#bullets-proj-list", ListView)
        b_idx = bullet_lv.index

        existing = None
        if not is_add and b_idx is not None and 0 <= b_idx < len(proj.bullets):
            b = proj.bullets[b_idx]
            existing = {"raw": b.raw, "tech": b.tech, "metric": b.metric}

        result = await self.app.push_screen_wait(BulletModal(bullet=existing))
        if result:
            from jobseeking_agent.models.user_profile import Bullet
            new_bullet = Bullet(**result)
            if is_add:
                proj.bullets.append(new_bullet)
            elif b_idx is not None and 0 <= b_idx < len(proj.bullets):
                proj.bullets[b_idx] = new_bullet
            self._refresh_proj_bullets()

    def _delete_proj_bullet(self) -> None:
        if self._sel_proj is None or not self._profile:
            return
        proj = self._profile.projects[self._sel_proj]
        b_idx = self.query_one("#bullets-proj-list", ListView).index
        if b_idx is not None and 0 <= b_idx < len(proj.bullets):
            proj.bullets.pop(b_idx)
            self._refresh_proj_bullets()

    # ── Unified button dispatcher ─────────────────────────────────────────────────

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        if btn_id == "btn-save":
            self._save_profile()

        # Skills
        elif btn_id == "btn-add-skill":
            self._add_skill()
        elif btn_id == "btn-update-skill":
            self._update_skill()
        elif btn_id == "btn-del-skill":
            self._delete_skill()

        # Experience
        elif btn_id == "btn-add-exp":
            self._add_experience()
        elif btn_id == "btn-del-exp":
            self._delete_experience()
        elif btn_id == "btn-add-exp-bullet":
            await self._edit_exp_bullet(is_add=True)
        elif btn_id == "btn-edit-exp-bullet":
            await self._edit_exp_bullet(is_add=False)
        elif btn_id == "btn-del-exp-bullet":
            self._delete_exp_bullet()

        # Projects
        elif btn_id == "btn-add-proj":
            self._add_project()
        elif btn_id == "btn-del-proj":
            self._delete_project()
        elif btn_id == "btn-add-proj-bullet":
            await self._edit_proj_bullet(is_add=True)
        elif btn_id == "btn-edit-proj-bullet":
            await self._edit_proj_bullet(is_add=False)
        elif btn_id == "btn-del-proj-bullet":
            self._delete_proj_bullet()
