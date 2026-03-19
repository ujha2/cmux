"""YAML file task source."""

from __future__ import annotations

from pathlib import Path

import yaml

from cmux.tasks.models import Task


class YamlSource:
    """Loads tasks from a YAML file."""

    def __init__(self, path: Path):
        self.path = path

    def load_tasks(self) -> list[Task]:
        """Load tasks from the YAML file."""
        if not self.path.exists():
            return []

        with open(self.path) as f:
            data = yaml.safe_load(f)

        if not data:
            return []

        tasks_data = data if isinstance(data, list) else data.get("tasks", [])
        tasks = []
        for item in tasks_data:
            if isinstance(item, str):
                tasks.append(Task(name=item[:30], description=item, source="yaml"))
            elif isinstance(item, dict):
                tasks.append(Task(
                    name=item.get("name", item.get("description", "task")[:30]),
                    description=item.get("description", item.get("name", "")),
                    skill=item.get("skill"),
                    source="yaml",
                    metadata=item.get("metadata", {}),
                ))
        return tasks
