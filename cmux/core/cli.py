"""Typer CLI: start, add, status, stop, skills, review, panes, attach, logs, dashboard."""

from __future__ import annotations

import subprocess
import sys
import uuid
import webbrowser
import platform
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from cmux.core.config import (
    CONFIG_FILE,
    DATA_DIR,
    SKILLS_DIR,
    TEMPLATES_DIR,
    get_mcp_servers,
    load_config,
    save_config,
    upsert_claude_mcp_command_server,
)
from cmux.skills.registry import SkillRegistry
from cmux.tasks.models import Task, TaskType
from cmux.tasks.queue import TaskQueue
from cmux.tasks.sources.workiq import WorkIQSource
from cmux.templates.cli import app as template_app
from cmux.templates.loader import TemplateLoader

app = typer.Typer(
    name="cmux",
    help="PM Command Center for Parallel AI Sessions",
    no_args_is_help=False,
    invoke_without_command=True,
)
app.add_typer(template_app, name="template")

console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Auto-init on first run, enter REPL when no subcommand given."""
    # Auto-init if config doesn't exist
    if not CONFIG_FILE.exists():
        config = load_config()
        _maybe_setup_workiq(config, first_time=True)
        save_config(config)
        console.print("[green]cmux auto-initialized.[/green]")

    # If no subcommand, enter REPL
    if ctx.invoked_subcommand is None:
        from cmux.core.repl import run_repl
        run_repl()


def _get_queue() -> TaskQueue:
    return TaskQueue()


def _get_registry() -> SkillRegistry:
    return SkillRegistry(user_skills_dir=SKILLS_DIR)


def _supports_interactive_prompts() -> bool:
    """Return True when interactive prompts are likely safe."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def _is_wsl() -> bool:
    """Return True when running inside WSL."""
    try:
        return "microsoft" in Path("/proc/version").read_text().lower()
    except Exception:
        return False


def _open_url(url: str) -> bool:
    """Best-effort URL open across native Linux, macOS, Windows, and WSL."""
    if _is_wsl():
        # Prefer wslview if available; fallback to Windows shell launch.
        for cmd in (["wslview", url], ["cmd.exe", "/c", "start", "", url]):
            try:
                result = subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if result.returncode == 0:
                    return True
            except FileNotFoundError:
                continue
            except Exception:
                continue
        return False

    try:
        if webbrowser.open(url):
            return True
    except Exception:
        pass

    system = platform.system()
    commands: list[list[str]] = []
    if system == "Darwin":
        commands = [["open", url]]
    elif system == "Linux":
        commands = [["xdg-open", url], ["gio", "open", url]]
    elif system == "Windows":
        commands = [["cmd", "/c", "start", "", url]]

    for cmd in commands:
        try:
            result = subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if result.returncode == 0:
                return True
        except FileNotFoundError:
            continue
        except Exception:
            continue

    return False


def _maybe_setup_workiq(config, first_time: bool = False) -> None:
    """Configure official @microsoft/workiq MCP registration defaults."""
    mcp_name = "workiq"
    mcp_command = "npx"
    mcp_args = _build_workiq_mcp_args(config)

    if _supports_interactive_prompts() and first_time:
        console.print(
            "[dim]Auto-configuring WorkIQ MCP:[/dim] "
            "npx -y @microsoft/workiq@latest mcp"
        )

    existing = get_mcp_servers()
    if existing and _supports_interactive_prompts():
        console.print(f"[dim]Claude MCP servers detected:[/dim] {', '.join(existing)}")

    save_config(config)

    try:
        upsert_claude_mcp_command_server(
            server_name=mcp_name,
            command=mcp_command,
            args=mcp_args,
            tools=["*"],
        )
        console.print("[green]WorkIQ configured and added to ~/.claude/settings.json[/green]")
    except Exception as e:
        console.print(f"[yellow]WorkIQ MCP registration failed:[/yellow] {e}")


def _fetch_workiq_tasks(server_url: str, include_focus: bool = True):
    """Fetch WorkIQ tasks via official stdio MCP (HTTP bridge optional fallback)."""
    config = load_config()
    source = WorkIQSource(
        mcp_server_url=server_url,
        mcp_args=_build_workiq_mcp_args(config),
    )
    try:
        return source.fetch_tasks(include_focus=include_focus)
    finally:
        source.close()


def _build_workiq_mcp_args(config) -> list[str]:
    """Build WorkIQ CLI args aligned to official workiq global options."""
    args = ["-y", "@microsoft/workiq@latest"]
    if config.workiq_account:
        args.extend(["--account", config.workiq_account])
    args.append("mcp")
    return args


def _pick_workiq_tasks(tasks: list[Task], add_all: bool) -> list[Task]:
    """Interactive selection for importing WorkIQ tasks."""
    if not tasks:
        return []
    if add_all:
        return tasks

    table = Table(title="WorkIQ Suggestions")
    table.add_column("#", width=4)
    table.add_column("Type", width=10)
    table.add_column("Task", style="cyan")
    table.add_column("Priority", width=8, style="yellow")

    for i, task in enumerate(tasks, 1):
        item_type = task.metadata.get("workiq_type", "item")
        table.add_row(f"#{i}", item_type, task.name, str(task.priority or 0))

    console.print(table)

    if not _supports_interactive_prompts():
        console.print("[dim]Non-interactive terminal detected. Use --add-all to import automatically.[/dim]")
        return []

    try:
        raw = console.input(
            "\n[cyan]Select items to add (e.g. 1 3 5), 'all', or Enter to cancel:[/cyan] "
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return []

    if not raw:
        return []
    if raw == "all":
        return tasks

    selected: list[Task] = []
    seen: set[int] = set()
    for tok in raw.split():
        try:
            idx = int(tok)
        except ValueError:
            continue
        if 1 <= idx <= len(tasks) and idx not in seen:
            selected.append(tasks[idx - 1])
            seen.add(idx)
    return selected


def _is_duplicate_workiq_task(existing: list[Task], incoming: Task) -> bool:
    """Detect duplicates by WorkIQ source id metadata."""
    in_id = incoming.metadata.get("workiq_id")
    in_type = incoming.metadata.get("workiq_type")
    if not in_id:
        return False
    for item in existing:
        if item.metadata.get("workiq_id") == in_id and item.metadata.get("workiq_type") == in_type:
            return True
    return False


def _build_prompt_and_tools(task: Task, registry: SkillRegistry, config=None):
    """Build the AI prompt and tool list for a task."""
    if config is None:
        config = load_config()
    loader = TemplateLoader(TEMPLATES_DIR)
    skill = registry.get(task.skill) if task.skill else None

    if skill:
        template_content = loader.load_for_skill(
            template_files=skill.definition.template_files,
            template_skill_map=config.template_skill_map,
            skill_name=skill.name,
        )
        prompt = skill.build_prompt(task.description, template_content)
        tools = skill.definition.tools
    else:
        prompt = task.description
        tools = []

    return prompt, tools


def _launch_task(task: Task, registry: SkillRegistry, config=None):
    """Launch a single task in a tmux pane."""
    from cmux.core.session import SessionManager

    if config is None:
        config = load_config()
    sm = SessionManager(config)
    prompt, tools = _build_prompt_and_tools(task, registry, config)

    try:
        pane_id = sm.launch_task(task, prompt, tools)
        console.print(f"[green]▶ Launched:[/green] {task.name} (pane {pane_id})")
        return pane_id
    except RuntimeError as e:
        console.print(f"[red]✗ {e}[/red]")
        return None


def _resolve_tasks(args: list[str], queue: TaskQueue) -> list[Task]:
    """Resolve a list of CLI arguments to tasks (indexes or IDs)."""
    tasks = []
    for arg in args:
        # Try as 1-based index
        try:
            idx = int(arg)
            task = queue.get_by_index(idx)
            if task:
                tasks.append(task)
                continue
        except ValueError:
            pass
        # Try as task ID / prefix
        task = queue.find(arg)
        if task:
            tasks.append(task)
        else:
            console.print(f"[red]Task not found: {arg}[/red]")
    return tasks


def _do_start(args: list[str]) -> None:
    """Core start logic, usable from both CLI and REPL."""
    config = load_config()
    registry = _get_registry()
    queue = _get_queue()

    # --all flag
    if args == ["--all"]:
        tasks = queue.pending()
        if not tasks:
            console.print("[dim]No pending agent tasks.[/dim]")
            return
    # --pick flag
    elif args == ["--pick"]:
        pending = queue.all_pending()
        if not pending:
            console.print("[dim]No pending tasks.[/dim]")
            return
        _show_numbered_tasks(pending)
        try:
            raw = console.input("\n[cyan]Enter task numbers (e.g. 1 3 5):[/cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if not raw:
            return
        args = raw.split()
        tasks = _resolve_tasks(args, queue)
    # Specific tasks by index/ID
    elif args:
        tasks = _resolve_tasks(args, queue)
    else:
        # No args: try pending agent tasks, else launch interactive
        tasks = queue.pending()
        if not tasks:
            console.print("[dim]No pending tasks. Launching interactive session...[/dim]")
            _launch_interactive(config)
            return

    if not tasks:
        return

    launched = 0
    for task in tasks:
        if task.task_type == TaskType.HUMAN:
            _start_human_task(task, queue)
            launched += 1
            continue

        if not task.skill:
            matched = registry.auto_match(task.description)
            if matched:
                task.skill = matched.name
                console.print(f"[dim]  Auto-matched skill: {matched.name}[/dim]")

        pane_id = _launch_task(task, registry, config)
        if pane_id:
            queue.mark_running(task.id)
            launched += 1
        else:
            break

    if launched:
        console.print(f"\n[cyan]{launched} session(s) launched.[/cyan] Use 'status' to monitor.")


def _launch_interactive(config) -> None:
    """Launch an interactive AI session in tmux."""
    from cmux.core.session import SessionManager

    sm = SessionManager(config)
    try:
        pane_id = sm.launch_interactive()
        console.print(f"[green]▶ Interactive session started[/green] (pane {pane_id})")
        console.print("[dim]Attach with: tmux attach -t cmux[/dim]")
    except Exception as e:
        console.print(f"[red]✗ {e}[/red]")


def _start_human_task(task: Task, queue: TaskQueue) -> None:
    """Start a pomodoro timer for a human task."""
    from cmux.core.pomodoro import run_pomodoro

    queue.mark_running(task.id)
    completed = run_pomodoro(task.name)
    if completed:
        queue.mark_done(task.id)
    else:
        # Stopped early — back to pending
        t = queue.get(task.id)
        if t:
            t.status = "pending"
            queue._save()


def _show_numbered_tasks(tasks: list[Task]) -> None:
    """Display a numbered task list."""
    table = Table(title="Pending Tasks")
    table.add_column("#", width=4)
    table.add_column("Type", width=4)
    table.add_column("ID", style="dim", width=10)
    table.add_column("Task", style="cyan")
    table.add_column("Skill", style="green")
    table.add_column("Pri", style="yellow", width=4)

    for i, task in enumerate(tasks, 1):
        icon = "🤖" if task.task_type == TaskType.AGENT else "👤"
        pri = str(task.priority) if task.priority else ""
        table.add_row(f"#{i}", icon, task.id, task.name, task.skill or "—", pri)

    console.print(table)


@app.command()
def start(
    targets: Optional[list[str]] = typer.Argument(None, help="Task index(es) or ID(s) to start"),
    preset: Optional[str] = typer.Option(None, "--preset", "-p", help="Preset name"),
    tasks_file: Optional[Path] = typer.Option(None, "--file", "-f", help="YAML tasks file"),
    all_tasks: bool = typer.Option(False, "--all", "-a", help="Start all pending agent tasks"),
    pick: bool = typer.Option(False, "--pick", help="Interactive task picker"),
):
    """Start cmux sessions. Launch by index, ID, preset, or interactively."""
    config = load_config()
    registry = _get_registry()
    queue = _get_queue()

    # Load from preset
    if preset:
        if preset in config.presets:
            preset_cfg = config.presets[preset]
            console.print(f"[cyan]Loading preset:[/cyan] {preset} — {preset_cfg.description}")
            for td in preset_cfg.tasks:
                queue.add(Task(
                    id=uuid.uuid4().hex[:8],
                    name=td.get("name", "task"),
                    description=td.get("description", td.get("name", "")),
                    skill=td.get("skill"),
                    source="preset",
                ))
        else:
            console.print(f"[red]Unknown preset: {preset}[/red]")
            raise typer.Exit(1)

    # Load from YAML file
    if tasks_file:
        loaded = queue.load_from_yaml(tasks_file)
        console.print(f"[cyan]Loaded {len(loaded)} tasks from {tasks_file}[/cyan]")

    # Build args for _do_start
    if all_tasks:
        _do_start(["--all"])
    elif pick:
        _do_start(["--pick"])
    elif targets:
        _do_start(targets)
    else:
        # Default: pending queue or interactive
        _do_start([])


@app.command()
def add(
    description: str = typer.Argument(..., help="Task description"),
    skill: Optional[str] = typer.Option(None, "--skill", "-s", help="Skill to use"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Task name"),
    human: bool = typer.Option(False, "--human", help="Mark as a human task (not AI)"),
    priority: int = typer.Option(0, "--priority", "-P", help="Priority (higher = more important)"),
    run: bool = typer.Option(False, "--run", "-r", help="Immediately launch the task"),
):
    """Add a task to the queue (and optionally run it immediately)."""
    registry = _get_registry()
    queue = _get_queue()

    task = queue.add_interactive(description, skill=skill, name=name)
    task.task_type = TaskType.HUMAN if human else TaskType.AGENT
    task.priority = priority
    queue._save()

    # Auto-match skill for agent tasks
    if not task.skill and task.task_type == TaskType.AGENT:
        matched = registry.auto_match(task.description)
        if matched:
            task.skill = matched.name
            queue._save()
            console.print(f"[dim]Auto-matched skill: {matched.name}[/dim]")

    icon = "🤖" if task.task_type == TaskType.AGENT else "👤"
    console.print(f"[green]+ Added:[/green] {icon} {task.name} (id: {task.id})")

    if not run:
        console.print("[dim]Run with: cmux start[/dim]")
        return

    if task.task_type == TaskType.HUMAN:
        _start_human_task(task, queue)
    else:
        pane_id = _launch_task(task, registry)
        if pane_id:
            queue.mark_running(task.id)


@app.command()
def status():
    """Show status of all running sessions and queued tasks."""
    queue = _get_queue()
    all_tasks = queue.all()

    if not all_tasks:
        console.print("[dim]No tasks in queue. Use 'add' to add one.[/dim]")
        return

    # Separate pending (numbered) and non-pending
    pending = queue.all_pending()
    non_pending = [t for t in all_tasks if t.status.value != "pending"]

    table = Table(title="Task Queue")
    table.add_column("#", width=4)
    table.add_column("Type", width=4)
    table.add_column("ID", style="dim", width=10)
    table.add_column("Task", style="cyan")
    table.add_column("Skill", style="green")
    table.add_column("Status")
    table.add_column("Pri", style="yellow", width=4)
    table.add_column("Source", style="dim")

    status_icons = {
        "pending": "⏳",
        "running": "🔄",
        "done": "✅",
        "error": "❌",
        "cancelled": "🚫",
    }

    for i, task in enumerate(pending, 1):
        icon = "🤖" if task.task_type == TaskType.AGENT else "👤"
        s_val = task.status.value if hasattr(task.status, 'value') else task.status
        s_icon = status_icons.get(s_val, "?")
        pri = str(task.priority) if task.priority else ""
        table.add_row(
            f"#{i}", icon, task.id, task.name,
            task.skill or "—", f"{s_icon} {s_val}", pri, task.source,
        )

    for task in non_pending:
        icon = "🤖" if task.task_type == TaskType.AGENT else "👤"
        s_val = task.status.value if hasattr(task.status, 'value') else task.status
        s_icon = status_icons.get(s_val, "?")
        pri = str(task.priority) if task.priority else ""
        table.add_row(
            "", icon, task.id, task.name,
            task.skill or "—", f"{s_icon} {s_val}", pri, task.source,
        )

    console.print(table)

    # Tmux pane info
    try:
        from cmux.core.session import SessionManager
        sm = SessionManager(load_config())
        pane_list = sm.get_active_panes()
        if pane_list:
            console.print(f"\n[cyan]{len(pane_list)} tmux pane(s) active.[/cyan]")
    except Exception:
        pass


@app.command()
def stop(
    pane_id: Optional[str] = typer.Argument(None, help="Pane ID to stop (or 'all')"),
):
    """Stop a running session or all sessions."""
    from cmux.core.session import SessionManager

    sm = SessionManager(load_config())

    if pane_id == "all" or pane_id is None:
        sm.stop_all()
        console.print("[yellow]Stopped all sessions.[/yellow]")
    else:
        sm.stop_task(pane_id)
        console.print(f"[yellow]Stopped session {pane_id}.[/yellow]")


@app.command("queue")
def queue_cmd(
    clear: bool = typer.Option(False, "--clear", "-c", help="Clear completed/cancelled tasks"),
    remove: Optional[str] = typer.Option(None, "--remove", "-r", help="Remove a task by ID"),
):
    """Manage the task queue."""
    q = _get_queue()

    if remove:
        if q.remove(remove):
            console.print(f"[green]Removed task {remove}[/green]")
        else:
            console.print(f"[red]Task {remove} not found[/red]")
        return

    if clear:
        count = q.clear_completed()
        console.print(f"[green]Cleared {count} completed task(s)[/green]")
        return

    status()


@app.command()
def review():
    """Interactively categorize pending tasks as human or agent."""
    queue = _get_queue()
    pending = queue.all_pending()

    if not pending:
        console.print("[dim]No pending tasks to review.[/dim]")
        return

    console.print("[bold cyan]Review pending tasks[/bold cyan] — categorize as agent (🤖) or human (👤)\n")

    changed = 0
    for i, task in enumerate(pending, 1):
        current = "🤖 agent" if task.task_type == TaskType.AGENT else "👤 human"
        console.print(f"  [cyan]#{i}[/cyan] {task.name}")
        console.print(f"      Currently: {current}")

        try:
            choice = console.input("      [a]gent / [h]uman / [s]kip? ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Review cancelled.[/dim]")
            break

        if choice in ("a", "agent"):
            task.task_type = TaskType.AGENT
            changed += 1
        elif choice in ("h", "human"):
            task.task_type = TaskType.HUMAN
            changed += 1
        # else skip

    if changed:
        queue._save()
        console.print(f"\n[green]Updated {changed} task(s).[/green]")
    else:
        console.print("\n[dim]No changes.[/dim]")


@app.command()
def panes():
    """Show all active tmux panes with task info."""
    from cmux.core.session import SessionManager

    sm = SessionManager(load_config())
    pane_list = sm.get_active_panes()

    if not pane_list:
        console.print("[dim]No active tmux panes.[/dim]")
        return

    table = Table(title="Active Panes")
    table.add_column("Pane ID", style="cyan")
    table.add_column("Task")
    table.add_column("Status")

    for p in pane_list:
        task = p["task"]
        task_name = task.name if task else "—"
        status_val = p["status"].value if hasattr(p["status"], "value") else str(p["status"])
        table.add_row(p["pane_id"], task_name, status_val)

    console.print(table)
    console.print("\n[dim]Tip: tmux attach -t cmux  |  cmux attach <pane_id>[/dim]")


@app.command()
def attach(
    target: str = typer.Argument(..., help="Pane ID or task index to focus"),
):
    """Focus a tmux pane by pane ID or task index."""
    from cmux.core.session import SessionManager

    sm = SessionManager(load_config())

    # Try as pane ID directly
    pane_list = sm.get_active_panes()
    pane_ids = [p["pane_id"] for p in pane_list]

    if target in pane_ids:
        sm.focus_pane(target)
        return

    # Try as task index → find matching pane
    try:
        idx = int(target)
        queue = _get_queue()
        task = queue.get_by_index(idx)
        if task:
            for p in pane_list:
                if p["task"] and p["task"].id == task.id:
                    sm.focus_pane(p["pane_id"])
                    return
            console.print(f"[red]Task #{idx} is not running in a pane.[/red]")
            return
    except ValueError:
        pass

    console.print(f"[red]Pane or task not found: {target}[/red]")


@app.command()
def logs(
    target: str = typer.Argument(..., help="Pane ID or task index to get logs from"),
):
    """Print captured output from a tmux pane."""
    from cmux.core.session import SessionManager

    sm = SessionManager(load_config())
    pane_list = sm.get_active_panes()

    pane_id = None
    # Direct pane ID
    for p in pane_list:
        if p["pane_id"] == target:
            pane_id = target
            break

    # Try as index
    if not pane_id:
        try:
            idx = int(target)
            queue = _get_queue()
            task = queue.get_by_index(idx)
            if task:
                for p in pane_list:
                    if p["task"] and p["task"].id == task.id:
                        pane_id = p["pane_id"]
                        break
        except ValueError:
            pass

    if not pane_id:
        console.print(f"[red]Pane or task not found: {target}[/red]")
        return

    output = sm.get_pane_output(pane_id)
    if output:
        console.print(output)
    else:
        console.print("[dim]No output captured.[/dim]")


@app.command()
def skills(
    match: Optional[str] = typer.Argument(None, help="Description to auto-match"),
):
    """List available skills, or match a description to a skill."""
    registry = _get_registry()

    if match:
        results = registry.match_with_scores(match)
        if results:
            table = Table(title=f"Skill matches for: '{match}'")
            table.add_column("Skill", style="cyan")
            table.add_column("Score", style="yellow")
            table.add_column("Description")
            for skill, score in results[:5]:
                table.add_row(skill.name, f"{score:.0%}", skill.description)
            console.print(table)
        else:
            console.print("[dim]No matching skills found.[/dim]")
        return

    table = Table(title="Available Skills")
    table.add_column("Skill", style="cyan")
    table.add_column("Description")
    table.add_column("Outputs", style="green")
    table.add_column("Manual Time", style="dim")

    for skill in registry.list_all():
        formats = ", ".join(f.value for f in skill.output_formats)
        time_est = f"~{skill.time_estimate_manual_minutes}m"
        table.add_row(skill.name, skill.description, formats, time_est)

    console.print(table)


@app.command()
def dashboard(
    stats: bool = typer.Option(False, "--stats", "-s", help="Show stats mode"),
):
    """Open the productivity dashboard TUI."""
    from cmux.dashboard.tui import run_dashboard
    run_dashboard(stats=stats)


@app.command("install-context-menu")
def install_context_menu():
    """Install right-click context menu (macOS Finder, Windows Explorer, or Linux Nautilus)."""
    from cmux.integrations.platform import install_context_menu as install
    install()


@app.command("uninstall-context-menu")
def uninstall_context_menu():
    """Remove right-click context menu integration."""
    from cmux.integrations.platform import uninstall_context_menu as uninstall
    uninstall()


@app.command()
def init():
    """Initialize cmux config and directories."""
    config = load_config()
    _maybe_setup_workiq(config, first_time=False)
    save_config(config)
    console.print("[green]cmux initialized![/green]")
    console.print(f"  Config: ~/.cmux/config.yaml")
    console.print(f"  Templates: ~/.cmux/templates/")
    console.print(f"  Skills: ~/.cmux/skills/")
    console.print(f"  Data: ~/.cmux/data/")
    console.print("\nNext steps:")
    console.print("  skills              — see available skills")
    console.print("  workiq-auth         — run WorkIQ auth/consent flow")
    console.print("  add 'description'   — add a task")
    console.print("  pull-workiq         — import from Microsoft WorkIQ")
    console.print("  start               — start sessions")


@app.command("workiq-auth")
def workiq_auth(
    tenant_id: Optional[str] = typer.Option(None, "--tenant-id", help="Entra tenant ID (used for admin consent URL)"),
    account: Optional[str] = typer.Option(None, "--account", help="Account hint to use for WorkIQ auth"),
    open_browser: bool = typer.Option(True, "--open-browser/--no-open-browser", help="Open browser for consent/sign-in guidance"),
    admin_consent: bool = typer.Option(False, "--admin-consent", help="Open tenant admin consent URL (requires --tenant-id)"),
):
    """Run WorkIQ EULA/auth flow so pull-workiq can access tenant data."""
    config = load_config()
    if tenant_id:
        config.workiq_tenant_id = tenant_id
    if account:
        config.workiq_account = account
    save_config(config)

    if open_browser:
        opened = False
        if admin_consent and config.workiq_tenant_id:
            consent_url = (
                f"https://login.microsoftonline.com/{config.workiq_tenant_id}"
                "/adminconsent?client_id=ba081686-5d24-4bc6-a0d6-d034ecffed87"
            )
            opened = _open_url(consent_url)
            if opened:
                console.print(f"[cyan]Opened admin consent URL:[/cyan] {consent_url}")
            else:
                console.print(f"[yellow]Could not auto-open admin consent URL. Open manually:[/yellow] {consent_url}")
        else:
            # User/admin portal landing page when tenant consent workflow is needed.
            entra_url = "https://entra.microsoft.com"
            opened = _open_url(entra_url)
            if opened:
                console.print("[cyan]Opened Microsoft Entra portal for consent/sign-in checks.[/cyan]")
            else:
                console.print(f"[yellow]Could not auto-open browser. Open manually:[/yellow] {entra_url}")

        if not opened:
            if _is_wsl():
                console.print("[dim]WSL tip: install wslu (wslview) or use Windows browser directly.[/dim]")

    cmd = ["npx", "-y", "@microsoft/workiq@latest"]
    if config.workiq_account:
        cmd.extend(["--account", config.workiq_account])
    cmd.append("accept-eula")

    console.print("[cyan]Running WorkIQ consent/EULA flow...[/cyan]")
    try:
        subprocess.run(cmd, check=False)
    except FileNotFoundError:
        console.print("[red]npx not found. Install Node.js first.[/red]")
        return

    console.print("[cyan]Running WorkIQ MCP readiness probe...[/cyan]")
    source = WorkIQSource(mcp_args=_build_workiq_mcp_args(config))
    try:
        tools = source.list_available_tools()
    except Exception as e:
        console.print(f"[yellow]WorkIQ probe failed:[/yellow] {e}")
        console.print("[dim]Complete browser sign-in/consent, then rerun 'workiq-auth'.[/dim]")
        console.print("[dim]If your org requires admin consent, run: workiq-auth --admin-consent --tenant-id <id>[/dim]")
        return
    finally:
        source.close()

    if tools:
        preview = ", ".join(tools[:6])
        more = "" if len(tools) <= 6 else f" (+{len(tools) - 6} more)"
        console.print(f"[green]WorkIQ MCP ready.[/green] Detected tools: {preview}{more}")
        console.print("[green]Auth flow complete. Try: cmux pull-workiq[/green]")
    else:
        console.print("[yellow]WorkIQ probe returned no tools.[/yellow]")
        console.print("[dim]This usually means consent is incomplete. If needed, use --admin-consent with tenant id.[/dim]")


@app.command("pull-workiq")
def pull_workiq(
    add_all: bool = typer.Option(False, "--add-all", help="Import all fetched WorkIQ items"),
    no_focus: bool = typer.Option(False, "--no-focus", help="Skip focus recommendations"),
):
    """Fetch WorkIQ tasks via stdio MCP (HTTP fallback optional), then review/add."""
    config = load_config()

    if not config.workiq_mcp_server:
        _maybe_setup_workiq(config, first_time=False)
        console.print("[dim]Using official @microsoft/workiq stdio MCP transport.[/dim]")
    else:
        console.print("[dim]Using stdio MCP first; HTTP bridge fallback is configured.[/dim]")
    if config.workiq_account:
        console.print(f"[dim]WorkIQ account hint:[/dim] {config.workiq_account}")

    try:
        tasks = _fetch_workiq_tasks(config.workiq_mcp_server, include_focus=not no_focus)
    except Exception as e:
        console.print(f"[red]Failed to fetch from WorkIQ MCP:[/red] {e}")
        console.print("[dim]Tip: run 'workiq-auth --open-browser' and, if needed, 'workiq-auth --admin-consent --tenant-id <id>'[/dim]")
        return

    if not tasks:
        console.print("[dim]No WorkIQ items found right now.[/dim]")
        return

    selected = _pick_workiq_tasks(tasks, add_all=add_all)
    if not selected:
        console.print("[dim]No items selected.[/dim]")
        return

    queue = _get_queue()
    registry = _get_registry()
    existing = queue.all()

    imported = 0
    skipped = 0
    for task in selected:
        if _is_duplicate_workiq_task(existing, task):
            skipped += 1
            continue

        if not task.skill:
            matched = registry.auto_match(task.description)
            if matched:
                task.skill = matched.name

        queue.add(task)
        existing.append(task)
        imported += 1

    console.print(f"[green]Imported {imported} WorkIQ task(s).[/green]")
    if skipped:
        console.print(f"[dim]Skipped {skipped} duplicate item(s).[/dim]")


if __name__ == "__main__":
    app()
