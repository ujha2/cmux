"""Tmux session/pane management using libtmux."""

from __future__ import annotations

import platform
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import libtmux

from cmux.backend.base import AIBackend
from cmux.backend.claude import ClaudeBackend
from cmux.backend.copilot import CopilotBackend
from cmux.core.config import load_config
from cmux.tasks.models import CmuxConfig, SessionStatus, Task, TaskStatus

SESSION_NAME = "cmux"


def get_backend(config: CmuxConfig) -> AIBackend:
    """Create the appropriate AI backend from config."""
    name = config.backend.backend
    if name == "claude":
        return ClaudeBackend(
            model=config.backend.claude_model,
            extra_args=config.backend.claude_args,
        )
    elif name == "copilot":
        return CopilotBackend()
    else:
        raise ValueError(f"Unknown backend: {name}")


def _notify(title: str, message: str) -> None:
    """Fire a native desktop notification."""
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(
                ["osascript", "-e", f'display notification "{message}" with title "{title}"'],
                check=False,
                capture_output=True,
            )
        elif system == "Linux":
            subprocess.run(
                ["notify-send", title, message],
                check=False,
                capture_output=True,
            )
    except FileNotFoundError:
        pass


class SessionManager:
    """Manages tmux sessions and panes for cmux tasks."""

    def __init__(self, config: CmuxConfig | None = None):
        self.config = config or load_config()
        self.server = libtmux.Server()
        self.backend = get_backend(self.config)
        self._tasks: dict[str, Task] = {}

    @property
    def session(self) -> libtmux.Session | None:
        """Get or return the cmux tmux session."""
        try:
            return self.server.sessions.get(session_name=SESSION_NAME)
        except Exception:
            return None

    def ensure_session(self) -> libtmux.Session:
        """Get existing cmux session or create a new one."""
        s = self.session
        if s is not None:
            return s
        return self.server.new_session(session_name=SESSION_NAME, attach=False)

    def launch_task(self, task: Task, prompt: str, tools: list[str] | None = None) -> str:
        """Launch a task in a new tmux pane. Returns pane ID."""
        session = self.ensure_session()

        active_count = len(self.get_active_panes())
        if active_count >= self.config.max_parallel_sessions:
            raise RuntimeError(
                f"Max parallel sessions ({self.config.max_parallel_sessions}) reached. "
                "Stop a session or increase max_parallel_sessions in config."
            )

        # Create output directory
        date_str = datetime.now().strftime("%Y-%m-%d")
        output_dir = Path(self.config.output_dir) / date_str / task.name
        task.output_dir = output_dir

        # Create a new pane (split from the first window)
        windows = session.windows
        if len(windows) == 1 and not self._tasks:
            pane = windows[0].panes[0]
        else:
            pane = windows[0].split_window(attach=False)

        pane_id = pane.pane_id

        # Update task state
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self._tasks[pane_id] = task

        # Launch via backend
        self.backend.launch_session(
            pane=pane,
            prompt=prompt,
            tools=tools or [],
            output_dir=output_dir,
        )

        return pane_id

    def launch_interactive(self) -> str:
        """Launch an interactive AI session with no predefined task. Returns pane ID."""
        session = self.ensure_session()

        windows = session.windows
        if len(windows) == 1 and not self._tasks:
            pane = windows[0].panes[0]
        else:
            pane = windows[0].split_window(attach=False)

        pane_id = pane.pane_id
        self.backend.launch_interactive(pane)
        return pane_id

    def get_active_panes(self) -> list[dict[str, Any]]:
        """Get info about all active cmux panes."""
        session = self.session
        if session is None:
            return []

        results = []
        for window in session.windows:
            for pane in window.panes:
                pid = pane.pane_id
                task = self._tasks.get(pid)
                status = self.backend.check_status(pane)

                # Notify on completion
                if task and status == SessionStatus.DONE and task.status == TaskStatus.RUNNING:
                    task.status = TaskStatus.DONE
                    task.completed_at = datetime.now()
                    _notify("cmux", f"Task completed: {task.name}")

                results.append({
                    "pane_id": pid,
                    "task": task,
                    "status": status,
                })
        return results

    def check_task_status(self, pane_id: str) -> SessionStatus:
        """Check the status of a specific task pane."""
        session = self.session
        if session is None:
            return SessionStatus.ERROR

        for window in session.windows:
            for pane in window.panes:
                if pane.pane_id == pane_id:
                    return self.backend.check_status(pane)
        return SessionStatus.ERROR

    def stop_task(self, pane_id: str) -> None:
        """Stop a running task."""
        session = self.session
        if session is None:
            return

        for window in session.windows:
            for pane in window.panes:
                if pane.pane_id == pane_id:
                    self.backend.stop_session(pane)
                    task = self._tasks.get(pane_id)
                    if task:
                        task.status = TaskStatus.CANCELLED
                        task.completed_at = datetime.now()
                    return

    def stop_all(self) -> None:
        """Stop all running tasks and kill the session."""
        session = self.session
        if session is None:
            return
        session.kill()
        for task in self._tasks.values():
            if task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()

    def focus_pane(self, pane_id: str) -> None:
        """Attach to the cmux session and focus a specific pane."""
        session = self.session
        if session is None:
            return
        for window in session.windows:
            for pane in window.panes:
                if pane.pane_id == pane_id:
                    pane.select()
                    session.attach()
                    return

    def get_pane_output(self, pane_id: str) -> str | None:
        """Capture and return the output from a specific pane."""
        session = self.session
        if session is None:
            return None
        for window in session.windows:
            for pane in window.panes:
                if pane.pane_id == pane_id:
                    return self.backend.get_output(pane)
        return None

    def get_task(self, pane_id: str) -> Task | None:
        return self._tasks.get(pane_id)

    @property
    def tasks(self) -> dict[str, Task]:
        return dict(self._tasks)
