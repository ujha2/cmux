"""Ad-hoc CLI input task source."""

from __future__ import annotations

import re

from cmux.tasks.models import Task


class InteractiveSource:
    """Creates tasks from ad-hoc CLI input."""

    def create_task(
        self,
        description: str,
        skill: str | None = None,
        name: str | None = None,
    ) -> Task:
        """Create a task from user-provided description."""
        if not name:
            name = self._generate_name(description)

        return Task(
            name=name,
            description=description,
            skill=skill,
            source="interactive",
        )

    def _generate_name(self, description: str) -> str:
        """Generate a short slug name from the description."""
        words = re.sub(r"[^a-zA-Z0-9\s]", "", description.lower()).split()
        slug = "-".join(words[:4])
        return slug or "task"
