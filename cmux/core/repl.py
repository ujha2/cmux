"""Interactive REPL for cmux — entered when bare `cmux` is run."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

HELP_TEXT = """[bold cyan]cmux commands:[/bold cyan]
  [green]add[/green] <description>     Add an agent task
  [green]add --human[/green] <desc>    Add a human task
  [green]start[/green] [index|id]      Start task(s) or interactive session
  [green]status[/green]                Show all tasks
  [green]stop[/green] [pane|all]       Stop sessions
  [green]review[/green]                Categorize pending tasks
  [green]skills[/green]                List available skills
  [green]panes[/green]                 Show tmux panes
  [green]help[/green]                  Show this help
  [green]quit[/green]                  Exit"""


def _show_task_context() -> None:
    """Show a brief numbered task list as context."""
    from cmux.tasks.queue import TaskQueue

    queue = TaskQueue()
    pending = queue.all_pending()
    if not pending:
        console.print("[dim]No pending tasks.[/dim]")
        return

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(width=4)
    table.add_column(width=3)
    table.add_column()
    table.add_column(width=10, style="dim")

    for i, task in enumerate(pending, 1):
        icon = "🤖" if task.task_type.value == "agent" else "👤"
        pri = f"p{task.priority}" if task.priority else ""
        table.add_row(f"#{i}", icon, task.name, pri)

    console.print(table)


def run_repl() -> None:
    """Main REPL loop."""
    console.print(Panel("[bold cyan]cmux[/bold cyan] — PM Command Center", border_style="cyan", width=50))
    _show_task_context()
    console.print("[dim]Type 'help' for commands, 'quit' to exit.[/dim]\n")

    while True:
        try:
            raw = console.input("[bold cyan]cmux>[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Bye.[/dim]")
            break

        if not raw:
            continue

        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd in ("quit", "exit", "q"):
            console.print("[dim]Bye.[/dim]")
            break
        elif cmd == "help":
            console.print(HELP_TEXT)
        elif cmd == "status":
            _repl_status()
        elif cmd == "add":
            _repl_add(arg)
        elif cmd == "start":
            _repl_start(arg)
        elif cmd == "stop":
            _repl_stop(arg)
        elif cmd == "review":
            _repl_review()
        elif cmd == "skills":
            _repl_skills()
        elif cmd == "panes":
            _repl_panes()
        else:
            console.print(f"[red]Unknown command: {cmd}[/red]. Type 'help'.")


def _repl_status() -> None:
    from cmux.core.cli import status as cli_status
    cli_status()


def _repl_add(arg: str) -> None:
    if not arg:
        console.print("[red]Usage: add <description>  or  add --human <description>[/red]")
        return

    from cmux.tasks.models import TaskType
    from cmux.tasks.queue import TaskQueue
    from cmux.skills.registry import SkillRegistry
    from cmux.core.config import SKILLS_DIR

    task_type = TaskType.AGENT
    desc = arg
    if arg.startswith("--human "):
        task_type = TaskType.HUMAN
        desc = arg[len("--human "):].strip()

    queue = TaskQueue()
    task = queue.add_interactive(desc)
    task.task_type = task_type
    queue._save()

    registry = SkillRegistry(user_skills_dir=SKILLS_DIR)
    if not task.skill and task_type == TaskType.AGENT:
        matched = registry.auto_match(task.description)
        if matched:
            task.skill = matched.name
            queue._save()
            console.print(f"[dim]Auto-matched skill: {matched.name}[/dim]")

    icon = "🤖" if task_type == TaskType.AGENT else "👤"
    console.print(f"[green]+ Added:[/green] {icon} {task.name} (id: {task.id})")


def _repl_start(arg: str) -> None:
    """Dispatch to the start command logic."""
    import typer
    from cmux.core.cli import _do_start
    try:
        _do_start(arg.split() if arg else [])
    except (typer.Exit, SystemExit):
        pass


def _repl_stop(arg: str) -> None:
    from cmux.core.session import SessionManager
    from cmux.core.config import load_config

    sm = SessionManager(load_config())
    target = arg.strip() or "all"
    if target == "all":
        sm.stop_all()
        console.print("[yellow]Stopped all sessions.[/yellow]")
    else:
        sm.stop_task(target)
        console.print(f"[yellow]Stopped session {target}.[/yellow]")


def _repl_review() -> None:
    from cmux.core.cli import review as cli_review
    cli_review()


def _repl_skills() -> None:
    from cmux.core.cli import skills as cli_skills
    cli_skills(match=None)


def _repl_panes() -> None:
    from cmux.core.cli import panes as cli_panes
    cli_panes()
