"""Base skill class for PM skills."""

from __future__ import annotations

from cmux.tasks.models import OutputFormat, SkillDef


class Skill:
    """A PM skill that can be executed by an AI backend."""

    def __init__(self, definition: SkillDef):
        self.definition = definition

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def description(self) -> str:
        return self.definition.description

    @property
    def output_formats(self) -> list[OutputFormat]:
        return self.definition.output_formats

    @property
    def time_estimate_manual_minutes(self) -> int:
        return self.definition.time_estimate_manual_minutes

    def build_prompt(self, task_description: str, template_content: str = "") -> str:
        """Build the full prompt for the AI backend."""
        prompt = self.definition.prompt_template.replace("{{task}}", task_description)

        if template_content:
            prompt += f"\n\n--- Personal Template ---\n{template_content}"

        return prompt

    def matches(self, text: str) -> float:
        """Score how well this skill matches a task description. Returns 0.0-1.0."""
        text_lower = text.lower()
        score = 0.0

        # Direct name match
        if self.name in text_lower:
            return 1.0

        # Alias match
        for alias in self.definition.aliases:
            if alias.lower() in text_lower:
                return 0.95

        # Keyword matching
        matched_keywords = sum(
            1 for kw in self.definition.keywords if kw.lower() in text_lower
        )
        if self.definition.keywords:
            score = matched_keywords / len(self.definition.keywords)

        return min(score, 1.0)
