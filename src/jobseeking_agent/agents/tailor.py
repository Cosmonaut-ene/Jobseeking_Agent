"""
Tailor Agent — compatibility shim for the legacy CLI/TUI layer.

The canonical implementation lives at backend.app.agents.tailor.
This module re-exports TailorAgent from there so that:
  1. There is a single source of truth for all tailor logic.
  2. Improvements to the backend agent are automatically available to the CLI.

NOTE: The CLI/TUI and the web backend always run as separate processes,
so there is no SQLModel metadata conflict from importing both package trees.
"""

from backend.app.agents.tailor import TailorAgent  # noqa: F401

__all__ = ["TailorAgent"]
