"""Productivity stats — SQLite-backed task history."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from cmux.core.config import DATA_DIR
from cmux.tasks.models import TaskHistory

DB_PATH = DATA_DIR / "history.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS task_history (
    task_id TEXT PRIMARY KEY,
    task_name TEXT NOT NULL,
    skill TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    status TEXT NOT NULL,
    tokens_used INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0.0,
    output_file_count INTEGER DEFAULT 0,
    output_total_bytes INTEGER DEFAULT 0,
    time_saved_minutes REAL DEFAULT 0.0
);
"""


class StatsDB:
    """SQLite database for task history and productivity stats."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def record(self, history: TaskHistory) -> None:
        """Record a completed task."""
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO task_history
                   (task_id, task_name, skill, started_at, completed_at, status,
                    tokens_used, cost_usd, output_file_count, output_total_bytes, time_saved_minutes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    history.task_id,
                    history.task_name,
                    history.skill,
                    history.started_at.isoformat(),
                    history.completed_at.isoformat(),
                    history.status,
                    history.tokens_used,
                    history.cost_usd,
                    history.output_file_count,
                    history.output_total_bytes,
                    history.time_saved_minutes,
                ),
            )

    def get_stats(self, since: datetime | None = None) -> dict:
        """Get aggregated stats, optionally filtered by time range."""
        where = ""
        params: list = []
        if since:
            where = "WHERE completed_at >= ?"
            params = [since.isoformat()]

        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                f"""SELECT
                    COUNT(*) as total_tasks,
                    COALESCE(SUM(tokens_used), 0) as total_tokens,
                    COALESCE(SUM(cost_usd), 0) as total_cost,
                    COALESCE(SUM(output_file_count), 0) as total_outputs,
                    COALESCE(SUM(time_saved_minutes), 0) as total_time_saved
                FROM task_history {where}""",
                params,
            ).fetchone()

            skill_counts = conn.execute(
                f"""SELECT skill, COUNT(*) as count
                FROM task_history {where}
                GROUP BY skill ORDER BY count DESC""",
                params,
            ).fetchall()

            day_counts = conn.execute(
                f"""SELECT strftime('%w', completed_at) as dow, COUNT(*) as count
                FROM task_history {where}
                GROUP BY dow ORDER BY dow""",
                params,
            ).fetchall()

        days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        by_day = {days[int(r["dow"])]: r["count"] for r in day_counts}

        return {
            "total_tasks": row["total_tasks"],
            "total_tokens": row["total_tokens"],
            "total_cost": row["total_cost"],
            "total_outputs": row["total_outputs"],
            "total_time_saved_minutes": row["total_time_saved"],
            "total_time_saved_hours": round(row["total_time_saved"] / 60, 1),
            "top_skills": {r["skill"]: r["count"] for r in skill_counts},
            "by_day": by_day,
        }

    def get_week_stats(self) -> dict:
        """Get stats for the current week."""
        now = datetime.now()
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        return self.get_stats(since=week_start)

    def get_all_stats(self) -> dict:
        """Get all-time stats."""
        return self.get_stats()

    def recent(self, limit: int = 20) -> list[dict]:
        """Get recent task history entries."""
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM task_history ORDER BY completed_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
