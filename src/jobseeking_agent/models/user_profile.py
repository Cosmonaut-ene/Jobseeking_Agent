"""
UserProfile is NOT stored in SQLite — it lives in data/user_profile.json.
This module defines the schema and provides a loader.
"""

import json
from pathlib import Path

from pydantic import BaseModel, Field


class Skill(BaseModel):
    name: str
    level: str  # beginner / intermediate / expert
    years: float = 0.0


class Bullet(BaseModel):
    raw: str                          # 原始描述，不可变事实锚点
    tech: list[str] = Field(default_factory=list)
    metric: str = ""


class Experience(BaseModel):
    company: str
    role: str
    duration: str                     # e.g. "2022-01 ~ 2024-06"
    bullets: list[Bullet] = Field(default_factory=list)


class Project(BaseModel):
    name: str
    description: str
    tech_stack: list[str] = Field(default_factory=list)
    bullets: list[Bullet] = Field(default_factory=list)


class Education(BaseModel):
    institution: str
    degree: str
    field: str = ""
    duration: str = ""   # "2018-03 ~ 2022-06"
    gpa: str = ""


class SalaryRange(BaseModel):
    min: int
    max: int
    currency: str = "AUD"


class Preferences(BaseModel):
    locations: list[str] = Field(default_factory=list)
    salary_range: SalaryRange | None = None
    job_types: list[str] = Field(default_factory=list)  # full-time / part-time / contract


class UserProfile(BaseModel):
    name: str
    target_roles: list[str]
    skills: list[Skill]
    experience: list[Experience]
    projects: list[Project]
    preferences: Preferences
    education: list[Education] = Field(default_factory=list)

    @classmethod
    def load(cls, path: Path | str = "data/user_profile.json") -> "UserProfile":
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(
                f"User profile not found at {p}. "
                "Copy data/user_profile.example.json to data/user_profile.json and fill it in."
            )
        return cls.model_validate(json.loads(p.read_text(encoding="utf-8")))

    def to_prompt_text(self) -> str:
        """Serialize profile to a compact text block for LLM prompts."""
        lines = [
            f"Name: {self.name}",
            f"Target roles: {', '.join(self.target_roles)}",
            f"Preferred locations: {', '.join(self.preferences.locations)}",
        ]
        if self.preferences.salary_range:
            sr = self.preferences.salary_range
            lines.append(f"Salary expectation: {sr.min}-{sr.max} {sr.currency}")

        lines.append("\n## Skills")
        for s in self.skills:
            lines.append(f"- {s.name} ({s.level}, {s.years}y)")

        lines.append("\n## Experience")
        for exp in self.experience:
            lines.append(f"\n### {exp.role} @ {exp.company} ({exp.duration})")
            for b in exp.bullets:
                lines.append(f"  - {b.raw}")

        lines.append("\n## Projects")
        for proj in self.projects:
            lines.append(f"\n### {proj.name}")
            lines.append(f"  Stack: {', '.join(proj.tech_stack)}")
            lines.append(f"  {proj.description}")
            for b in proj.bullets:
                lines.append(f"  - {b.raw}")

        if self.education:
            lines.append("\n## Education")
            for edu in self.education:
                lines.append(f"  {edu.degree} in {edu.field} @ {edu.institution} ({edu.duration})")

        return "\n".join(lines)
