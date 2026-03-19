"""Work IQ MCP client — pulls tasks from Microsoft 365 via MCP."""

from __future__ import annotations

from typing import Any

import httpx

from cmux.tasks.models import Task


class WorkIQSource:
    """Connects to Work IQ MCP server to pull emails, calendar, and tasks."""

    def __init__(self, mcp_server_url: str | None = None):
        self.mcp_server_url = mcp_server_url
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        """Connect to the Work IQ MCP server."""
        if not self.mcp_server_url:
            raise ValueError(
                "Work IQ MCP server URL not configured. "
                "Set workiq_mcp_server in ~/.cmux/config.yaml"
            )
        self._client = httpx.AsyncClient(base_url=self.mcp_server_url)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()

    async def fetch_tasks(self) -> list[Task]:
        """Fetch actionable items from Work IQ."""
        if not self._client:
            await self.connect()

        tasks = []

        # Fetch emails needing action
        emails = await self._call_tool("get_action_emails")
        for email in emails:
            tasks.append(Task(
                name=f"email-{email.get('subject', 'untitled')[:25]}",
                description=f"Respond to email: {email.get('subject', '')}. {email.get('summary', '')}",
                source="workiq",
                metadata={"workiq_type": "email", "workiq_id": email.get("id")},
            ))

        # Fetch calendar prep items
        meetings = await self._call_tool("get_upcoming_meetings")
        for meeting in meetings:
            tasks.append(Task(
                name=f"prep-{meeting.get('title', 'meeting')[:25]}",
                description=f"Prepare for meeting: {meeting.get('title', '')}. {meeting.get('agenda', '')}",
                source="workiq",
                metadata={"workiq_type": "meeting", "workiq_id": meeting.get("id")},
            ))

        # Fetch assigned tasks
        work_tasks = await self._call_tool("get_assigned_tasks")
        for wt in work_tasks:
            tasks.append(Task(
                name=f"task-{wt.get('title', 'item')[:25]}",
                description=wt.get("description", wt.get("title", "")),
                source="workiq",
                metadata={"workiq_type": "task", "workiq_id": wt.get("id")},
            ))

        return tasks

    async def _call_tool(self, tool_name: str, args: dict[str, Any] | None = None) -> list[dict]:
        """Call an MCP tool on the Work IQ server."""
        if not self._client:
            return []
        try:
            response = await self._client.post(
                "/mcp/tools/call",
                json={"tool": tool_name, "arguments": args or {}},
            )
            response.raise_for_status()
            result = response.json()
            return result.get("content", [])
        except Exception:
            return []
