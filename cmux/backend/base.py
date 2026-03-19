"""Abstract AI backend interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import libtmux

from cmux.tasks.models import SessionStatus


class AIBackend(ABC):
    """Abstract base class for AI backends (Claude, Copilot, etc.)."""

    @abstractmethod
    def launch_session(
        self,
        pane: libtmux.Pane,
        prompt: str,
        tools: list[str],
        output_dir: Path,
    ) -> None:
        """Launch an AI session in the given tmux pane."""
        ...

    @abstractmethod
    def check_status(self, pane: libtmux.Pane) -> SessionStatus:
        """Check the status of a session running in the given pane."""
        ...

    @abstractmethod
    def get_output(self, pane: libtmux.Pane) -> str:
        """Get the current output text from the pane."""
        ...

    @abstractmethod
    def stop_session(self, pane: libtmux.Pane) -> None:
        """Stop the AI session in the given pane."""
        ...

    @abstractmethod
    def launch_interactive(self, pane: libtmux.Pane) -> None:
        """Launch an interactive AI session (no prompt, human drives)."""
        ...
