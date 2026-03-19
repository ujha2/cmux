"""Load user templates from ~/.cmux/templates/."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


class TemplateLoader:
    """Loads and processes personal templates."""

    def __init__(self, templates_dir: Path):
        self.templates_dir = templates_dir

    def list_templates(self) -> list[dict[str, str]]:
        """List all available templates."""
        if not self.templates_dir.exists():
            return []
        results = []
        for path in sorted(self.templates_dir.glob("*.md")):
            results.append({
                "name": path.stem,
                "path": str(path),
                "size": f"{path.stat().st_size} bytes",
            })
        return results

    def load(self, name: str) -> str | None:
        """Load a template by name (without extension)."""
        path = self.templates_dir / f"{name}.md"
        if path.exists():
            return path.read_text()
        return None

    def load_for_skill(
        self,
        template_files: list[str],
        template_skill_map: dict[str, list[str]] | None = None,
        skill_name: str = "",
    ) -> str:
        """Load and combine templates relevant to a skill."""
        contents = []

        # Load explicitly listed template files
        for tf in template_files:
            name = tf.replace(".md", "")
            content = self.load(name)
            if content:
                contents.append(f"# Template: {name}\n{content}")

        # Load templates from skill map in config
        if template_skill_map and skill_name:
            for tpl_name, skills in template_skill_map.items():
                if skill_name in skills:
                    content = self.load(tpl_name)
                    if content:
                        contents.append(f"# Template: {tpl_name}\n{content}")

        combined = "\n\n".join(contents)
        return self._substitute_variables(combined)

    def _substitute_variables(self, text: str) -> str:
        """Replace template variables with actual values."""
        now = datetime.now()
        replacements = {
            "{{date}}": now.strftime("%Y-%m-%d"),
            "{{year}}": str(now.year),
            "{{quarter}}": f"Q{(now.month - 1) // 3 + 1}",
            "{{month}}": now.strftime("%B"),
            "{{week}}": str(now.isocalendar()[1]),
        }
        for var, val in replacements.items():
            text = text.replace(var, val)
        return text

    def create(self, name: str, content: str = "") -> Path:
        """Create a new template file."""
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        path = self.templates_dir / f"{name}.md"
        if not content:
            content = f"# {name.replace('_', ' ').title()} Template\n\n<!-- Add your rules and examples here -->\n"
        path.write_text(content)
        return path
