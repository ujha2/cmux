"""Unified task queue — persisted to ~/.cmux/queue.json between invocations."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from cmux.core.config import CMUX_HOME
from cmux.tasks.models import Task, TaskType
from cmux.tasks.sources.interactive import InteractiveSource
from cmux.tasks.sources.yaml_source import YamlSource

QUEUE_FILE = CMUX_HOME / "queue.json"


class TaskQueue:
    """Manages a persistent queue of tasks across CLI invocations."""

    def __init__(self):
        self._tasks: list[Task] = []
        self._load()

    def _load(self) -> None:
        """Load tasks from the persistent queue file."""
        if QUEUE_FILE.exists():
            try:
                data = json.loads(QUEUE_FILE.read_text())
                self._tasks = [Task(**t) for t in data]
            except (json.JSONDecodeError, Exception):
                self._tasks = []

    def _save(self) -> None:
        """Save tasks to the persistent queue file."""
        QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = [json.loads(t.model_dump_json()) for t in self._tasks]
        QUEUE_FILE.write_text(json.dumps(data, indent=2))

    def add(self, task: Task) -> Task:
        """Add a task to the queue."""
        if not task.id:
            task.id = uuid.uuid4().hex[:8]
        self._tasks.append(task)
        self._save()
        return task

    def add_interactive(self, description: str, skill: str | None = None, name: str | None = None) -> Task:
        """Add a task from interactive CLI input."""
        source = InteractiveSource()
        task = source.create_task(description=description, skill=skill, name=name)
        return self.add(task)

    def load_from_yaml(self, path: Path) -> list[Task]:
        """Load tasks from a YAML file."""
        source = YamlSource(path)
        tasks = source.load_tasks()
        for t in tasks:
            self.add(t)
        return tasks

    def pending(self, include_human: bool = False) -> list[Task]:
        """Return pending tasks sorted by priority (desc). By default only agent tasks."""
        tasks = [t for t in self._tasks if t.status.value == "pending"]
        if not include_human:
            tasks = [t for t in tasks if t.task_type == TaskType.AGENT]
        return sorted(tasks, key=lambda t: t.priority, reverse=True)

    def all_pending(self) -> list[Task]:
        """Return all pending tasks (both agent and human), sorted by priority desc."""
        tasks = [t for t in self._tasks if t.status.value == "pending"]
        return sorted(tasks, key=lambda t: t.priority, reverse=True)

    def all(self) -> list[Task]:
        """Return all tasks."""
        return list(self._tasks)

    def get(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        for t in self._tasks:
            if t.id == task_id:
                return t
        return None

    def find(self, identifier: str) -> Task | None:
        """Find a task by exact ID or prefix match."""
        # Exact match first
        task = self.get(identifier)
        if task:
            return task
        # Prefix match
        matches = [t for t in self._tasks if t.id.startswith(identifier)]
        if len(matches) == 1:
            return matches[0]
        return None

    def get_by_index(self, index: int) -> Task | None:
        """Get a pending task by 1-based index (from the display order)."""
        tasks = self.all_pending()
        if 1 <= index <= len(tasks):
            return tasks[index - 1]
        return None

    def mark_running(self, task_id: str) -> None:
        """Mark a task as running."""
        task = self.get(task_id)
        if task:
            task.status = "running"
            self._save()

    def mark_done(self, task_id: str) -> None:
        """Mark a task as done."""
        task = self.get(task_id)
        if task:
            task.status = "done"
            self._save()

    def remove(self, task_id: str) -> bool:
        """Remove a task by ID."""
        for i, t in enumerate(self._tasks):
            if t.id == task_id:
                self._tasks.pop(i)
                self._save()
                return True
        return False

    def clear_completed(self) -> int:
        """Remove all completed/cancelled tasks. Returns count removed."""
        before = len(self._tasks)
        self._tasks = [t for t in self._tasks if t.status.value in ("pending", "running")]
        self._save()
        return before - len(self._tasks)
