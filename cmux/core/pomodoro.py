"""Pomodoro timer for human tasks — rich Live countdown display."""

from __future__ import annotations

import time

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from cmux.core.session import _notify


def run_pomodoro(task_name: str, minutes: int = 25) -> bool:
    """Run a pomodoro countdown timer. Returns True if completed, False if interrupted."""
    console = Console()
    total_seconds = minutes * 60
    remaining = total_seconds

    console.print(f"\n[bold cyan]Pomodoro started:[/bold cyan] {task_name}")
    console.print(f"[dim]{minutes} minutes — press Ctrl+C to stop early[/dim]\n")

    try:
        with Live(console=console, refresh_per_second=1) as live:
            while remaining > 0:
                mins, secs = divmod(remaining, 60)
                pct = (total_seconds - remaining) / total_seconds
                bar_width = 30
                filled = int(bar_width * pct)
                bar = "█" * filled + "░" * (bar_width - filled)

                display = Text()
                display.append(f"  {mins:02d}:{secs:02d}", style="bold white")
                display.append(f"  [{bar}]  ", style="cyan")
                display.append(f"{pct:.0%}", style="dim")

                panel = Panel(
                    display,
                    title=f"👤 {task_name}",
                    border_style="cyan",
                    width=60,
                )
                live.update(panel)
                time.sleep(1)
                remaining -= 1

        _notify("cmux", f"Pomodoro done: {task_name}")
        console.print(f"\n[bold green]Pomodoro complete![/bold green] {task_name}")
        return True
    except KeyboardInterrupt:
        console.print(f"\n[yellow]Pomodoro stopped early.[/yellow] {task_name}")
        return False
