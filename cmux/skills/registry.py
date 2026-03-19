"""Skill lookup, auto-matching, and user-defined skill loading."""

from __future__ import annotations

from pathlib import Path

import yaml

from cmux.skills.base import Skill
from cmux.skills.builtins import (
    brainstorm_reflect,
    competitive_research,
    copywriting,
    data_analysis,
    deck,
    golden_set,
    one_pager,
    prd_spec,
    prototype,
    status_update,
)
from cmux.tasks.models import SkillDef

BUILTIN_SKILLS = [
    one_pager.definition,
    prd_spec.definition,
    deck.definition,
    competitive_research.definition,
    prototype.definition,
    data_analysis.definition,
    status_update.definition,
    brainstorm_reflect.definition,
    copywriting.definition,
    golden_set.definition,
]


class SkillRegistry:
    """Registry of all available skills (built-in + user-defined)."""

    def __init__(self, user_skills_dir: Path | None = None):
        self._skills: dict[str, Skill] = {}
        self._load_builtins()
        if user_skills_dir:
            self._load_user_skills(user_skills_dir)

    def _load_builtins(self) -> None:
        for defn in BUILTIN_SKILLS:
            self._skills[defn.name] = Skill(defn)

    def _load_user_skills(self, skills_dir: Path) -> None:
        if not skills_dir.exists():
            return
        for path in skills_dir.glob("*.yaml"):
            try:
                with open(path) as f:
                    data = yaml.safe_load(f)
                if data:
                    defn = SkillDef(**data)
                    self._skills[defn.name] = Skill(defn)
            except Exception:
                pass  # Skip malformed skill files

    def get(self, name: str) -> Skill | None:
        """Get a skill by exact name."""
        return self._skills.get(name)

    def list_all(self) -> list[Skill]:
        """Return all registered skills."""
        return list(self._skills.values())

    def auto_match(self, description: str) -> Skill | None:
        """Find the best-matching skill for a task description."""
        best_skill = None
        best_score = 0.0

        for skill in self._skills.values():
            score = skill.matches(description)
            if score > best_score:
                best_score = score
                best_skill = skill

        if best_score >= 0.3:
            return best_skill
        return None

    def match_with_scores(self, description: str) -> list[tuple[Skill, float]]:
        """Return all skills with their match scores, sorted by score descending."""
        results = []
        for skill in self._skills.values():
            score = skill.matches(description)
            if score > 0.0:
                results.append((skill, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results
