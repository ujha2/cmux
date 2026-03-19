"""Template management CLI commands."""

from __future__ import annotations

import os
import subprocess

import typer
from rich.console import Console
from rich.table import Table

from cmux.core.config import TEMPLATES_DIR, load_config
from cmux.templates.loader import TemplateLoader

app = typer.Typer(help="Manage personal templates")
console = Console()


@app.command("list")
def list_templates():
    """List all personal templates."""
    loader = TemplateLoader(TEMPLATES_DIR)
    templates = loader.list_templates()

    if not templates:
        console.print("[dim]No templates found. Create one with: cmux template create <name>[/dim]")
        return

    config = load_config()
    skill_map = config.template_skill_map

    table = Table(title="Personal Templates")
    table.add_column("Name", style="cyan")
    table.add_column("Size", style="dim")
    table.add_column("Used by Skills", style="green")

    for tpl in templates:
        name = tpl["name"]
        used_by = []
        for tpl_name, skills in skill_map.items():
            if tpl_name == name:
                used_by.extend(skills)
        table.add_row(name, tpl["size"], ", ".join(used_by) if used_by else "—")

    console.print(table)


@app.command("edit")
def edit_template(name: str):
    """Open a template in $EDITOR."""
    path = TEMPLATES_DIR / f"{name}.md"
    if not path.exists():
        console.print(f"[red]Template '{name}' not found.[/red]")
        raise typer.Exit(1)

    editor = os.environ.get("EDITOR", "vim")
    subprocess.run([editor, str(path)])


@app.command("create")
def create_template(name: str, content: str = typer.Option("", help="Initial content")):
    """Create a new template."""
    loader = TemplateLoader(TEMPLATES_DIR)
    path = loader.create(name, content)
    console.print(f"[green]Created template:[/green] {path}")
    console.print("[dim]Edit with: cmux template edit " + name + "[/dim]")


@app.command("show")
def show_template(name: str):
    """Display a template's contents."""
    loader = TemplateLoader(TEMPLATES_DIR)
    content = loader.load(name)
    if content is None:
        console.print(f"[red]Template '{name}' not found.[/red]")
        raise typer.Exit(1)
    console.print(content)
