"""Claude Code backend — launches claude CLI in tmux panes."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import libtmux

from cmux.backend.base import AIBackend
from cmux.tasks.models import SessionStatus


class ClaudeBackend(AIBackend):
    """Backend that runs Claude Code CLI sessions."""

    def __init__(self, model: str = "claude-sonnet-4-6", extra_args: list[str] | None = None):
        self.model = model
        self.extra_args = extra_args or []

    def launch_session(
        self,
        pane: libtmux.Pane,
        prompt: str,
        tools: list[str],
        output_dir: Path,
    ) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)

        cmd_parts = ["claude", "--print"]
        if self.model:
            cmd_parts.extend(["--model", self.model])
        if tools:
            cmd_parts.extend(["--allowedTools", ",".join(tools)])
        cmd_parts.extend(self.extra_args)

        safe_prompt = prompt.replace("'", "'\\''")
        cmd_parts.extend(["-p", f"'{safe_prompt}'"])

        full_cmd = " ".join(cmd_parts) + f" | tee '{output_dir}/output.md'"
        pane.send_keys(full_cmd, enter=True)

    def check_status(self, pane: libtmux.Pane) -> SessionStatus:
        pane_content = self.get_output(pane)
        if not pane_content.strip():
            return SessionStatus.LAUNCHING

        last_lines = pane_content.strip().split("\n")[-5:]
        last_text = "\n".join(last_lines).lower()

        if "$" in last_text and "claude" not in last_text:
            return SessionStatus.DONE
        if "error" in last_text or "fatal" in last_text:
            return SessionStatus.ERROR
        return SessionStatus.RUNNING

    def get_output(self, pane: libtmux.Pane) -> str:
        lines = pane.capture_pane()
        return "\n".join(lines)

    def stop_session(self, pane: libtmux.Pane) -> None:
        pane.send_keys("C-c", enter=False)

    def launch_interactive(self, pane: libtmux.Pane) -> None:
        """Launch interactive claude session (no --print, no prompt)."""
        cmd_parts = ["claude"]
        if self.model:
            cmd_parts.extend(["--model", self.model])
        cmd_parts.extend(self.extra_args)
        pane.send_keys(" ".join(cmd_parts), enter=True)

    def parse_token_count(self, output: str) -> int:
        """Parse token usage from Claude output."""
        match = re.search(r"(\d[\d,]+)\s*tokens?", output)
        if match:
            return int(match.group(1).replace(",", ""))
        return 0

    def parse_cost(self, output: str) -> float:
        """Parse cost from Claude output."""
        match = re.search(r"\$(\d+\.?\d*)", output)
        if match:
            return float(match.group(1))
        return 0.0
