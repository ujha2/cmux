"""Copilot CLI backend — future implementation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import libtmux

from cmux.backend.base import AIBackend
from cmux.tasks.models import SessionStatus


class CopilotBackend(AIBackend):
    """Placeholder backend for GitHub Copilot CLI. Not yet implemented."""

    def launch_session(
        self,
        pane: libtmux.Pane,
        prompt: str,
        tools: list[str],
        output_dir: Path,
    ) -> None:
        raise NotImplementedError(
            "Copilot backend is not yet implemented. "
            "Set backend: claude in ~/.cmux/config.yaml"
        )

    def check_status(self, pane: libtmux.Pane) -> SessionStatus:
        raise NotImplementedError("Copilot backend is not yet implemented.")

    def get_output(self, pane: libtmux.Pane) -> str:
        raise NotImplementedError("Copilot backend is not yet implemented.")

    def stop_session(self, pane: libtmux.Pane) -> None:
        raise NotImplementedError("Copilot backend is not yet implemented.")

    def launch_interactive(self, pane: libtmux.Pane) -> None:
        raise NotImplementedError("Copilot backend is not yet implemented.")
