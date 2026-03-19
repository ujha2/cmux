"""Textual TUI — live session monitor and stats dashboard."""

from __future__ import annotations

from datetime import datetime

from rich.table import Table
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.widgets import Footer, Header, Static

from cmux.dashboard.stats import StatsDB
from cmux.tasks.queue import TaskQueue


class LivePanel(Static):
    """Panel showing active sessions and queued tasks."""

    def render(self) -> Table:
        table = Table(title="Task Queue & Sessions", expand=True)
        table.add_column("", width=4)
        table.add_column("Task", style="cyan")
        table.add_column("Skill", style="green")
        table.add_column("Status")
        table.add_column("Source", style="dim")

        queue = TaskQueue()
        tasks = queue.all()

        for task in tasks:
            icon = {
                "pending": "⏳",
                "running": "🔄",
                "done": "✅",
                "error": "❌",
                "cancelled": "🚫",
            }.get(task.status.value if hasattr(task.status, 'value') else str(task.status), "?")
            status_val = task.status.value if hasattr(task.status, 'value') else str(task.status)
            table.add_row(icon, task.name, task.skill or "—", status_val, task.source)

        if not tasks:
            table.add_row("—", "No tasks yet", "—", "—", "—")

        # Try to show tmux session info
        try:
            from cmux.core.config import load_config
            from cmux.core.session import SessionManager
            sm = SessionManager(load_config())
            panes = sm.get_active_panes()
            if panes:
                table.add_section()
                for info in panes:
                    t = info["task"]
                    st = info["status"]
                    s_icon = {"running": "🔄", "done": "✅", "error": "❌", "launching": "⏳"}.get(st.value, "?")
                    table.add_row(s_icon, t.name if t else info["pane_id"], t.skill if t else "—", st.value, "tmux")
        except Exception:
            pass

        return table


class StatsPanel(Static):
    """Panel showing productivity stats."""

    def __init__(self, stats_db: StatsDB):
        super().__init__()
        self.stats_db = stats_db

    def render(self) -> Table:
        week = self.stats_db.get_week_stats()
        alltime = self.stats_db.get_all_stats()

        table = Table(title="Productivity Stats", expand=True)
        table.add_column("Metric", style="cyan")
        table.add_column("This Week", style="green")
        table.add_column("All Time", style="yellow")

        table.add_row("Tasks", str(week["total_tasks"]), str(alltime["total_tasks"]))
        table.add_row(
            "Time saved",
            f"~{week['total_time_saved_hours']}h",
            f"~{alltime['total_time_saved_hours']}h",
        )
        table.add_row(
            "Tokens", f"{week['total_tokens']:,}", f"{alltime['total_tokens']:,}"
        )
        table.add_row(
            "Cost", f"${week['total_cost']:.2f}", f"${alltime['total_cost']:.2f}"
        )
        table.add_row("Outputs", str(week["total_outputs"]), str(alltime["total_outputs"]))

        return table


class SkillStatsPanel(Static):
    """Panel showing top skills and usage by day."""

    def __init__(self, stats_db: StatsDB):
        super().__init__()
        self.stats_db = stats_db

    def render(self) -> Table:
        alltime = self.stats_db.get_all_stats()

        table = Table(title="Skill Usage", expand=True)
        table.add_column("Skill", style="cyan")
        table.add_column("Count", style="green")
        table.add_column("", width=20)

        max_count = max(alltime["top_skills"].values()) if alltime["top_skills"] else 1
        for skill, count in list(alltime["top_skills"].items())[:8]:
            bar_len = int((count / max_count) * 16)
            bar = "█" * bar_len
            table.add_row(skill, str(count), bar)

        if not alltime["top_skills"]:
            table.add_row("—", "No data yet", "")

        return table


class DashboardApp(App):
    """Cmux dashboard TUI application."""

    TITLE = "cmux dashboard"
    CSS = """
    Screen {
        layout: vertical;
    }
    #main-panel {
        height: 1fr;
    }
    """
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("s", "toggle_stats", "Stats"),
    ]

    def __init__(self, show_stats: bool = False):
        super().__init__()
        self.show_stats = show_stats
        self.stats_db = StatsDB()

    def compose(self) -> ComposeResult:
        yield Header()
        if self.show_stats:
            yield Vertical(
                StatsPanel(self.stats_db),
                SkillStatsPanel(self.stats_db),
                id="main-panel",
            )
        else:
            yield Vertical(
                LivePanel(),
                id="main-panel",
            )
        yield Footer()

    def action_refresh(self) -> None:
        self.refresh()

    def action_toggle_stats(self) -> None:
        self.show_stats = not self.show_stats
        # Remount with new panels
        self.query_one("#main-panel").remove()
        if self.show_stats:
            self.mount(Vertical(
                StatsPanel(self.stats_db),
                SkillStatsPanel(self.stats_db),
                id="main-panel",
            ), before=self.query_one(Footer))
        else:
            self.mount(Vertical(
                LivePanel(),
                id="main-panel",
            ), before=self.query_one(Footer))


def run_dashboard(stats: bool = False) -> None:
    """Run the dashboard TUI."""
    app = DashboardApp(show_stats=stats)
    app.run()
