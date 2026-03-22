"""Work IQ MCP client — pulls tasks from Microsoft 365 via MCP."""

from __future__ import annotations

import json
import re
import select
import subprocess
import time
from typing import Any

import httpx

from cmux.tasks.models import Task


class WorkIQSource:
    """Connects to Work IQ MCP server to pull emails, calendar, and tasks."""

    def __init__(
        self,
        mcp_server_url: str | None = None,
        mcp_command: str = "npx",
        mcp_args: list[str] | None = None,
    ):
        self.mcp_server_url = mcp_server_url
        self.mcp_command = mcp_command
        self.mcp_args = mcp_args or ["-y", "@microsoft/workiq@latest", "mcp"]
        self._http_client: httpx.Client | None = None
        self._proc: subprocess.Popen[bytes] | None = None
        self._next_id = 1
        self._stdio_mode = "lsp"

    def connect_http(self) -> None:
        """Connect to an HTTP MCP bridge endpoint."""
        if not self.mcp_server_url:
            raise ValueError("Work IQ MCP bridge URL not configured.")
        self._http_client = httpx.Client(base_url=self.mcp_server_url, timeout=20.0)

    def connect_stdio(self) -> None:
        """Start the official @microsoft/workiq MCP stdio server process."""
        if self._proc is not None:
            return
        # Try standard MCP Content-Length framing first, then json-lines fallback.
        self._stdio_mode = "lsp"
        self._start_process()
        try:
            self._initialize_session(timeout=30.0)
            return
        except TimeoutError:
            self.close()

        self._stdio_mode = "jsonl"
        self._start_process()
        self._initialize_session(timeout=30.0)

    def _start_process(self) -> None:
        self._proc = subprocess.Popen(
            [self.mcp_command, *self.mcp_args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def _initialize_session(self, timeout: float) -> None:
        init_result = self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "cmux", "version": "0.1.0"},
            },
            timeout=timeout,
        )
        if not isinstance(init_result, dict):
            raise RuntimeError("Failed to initialize MCP session with WorkIQ.")
        self._notify("notifications/initialized", {})

    def close(self) -> None:
        if self._http_client:
            self._http_client.close()
            self._http_client = None

        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=2)
            except Exception:
                self._proc.kill()
            finally:
                self._proc = None

    def fetch_tasks(self, include_focus: bool = True) -> list[Task]:
        """Fetch actionable items from Work IQ, preferring stdio MCP."""
        errors: list[str] = []

        try:
            return self._fetch_tasks_stdio(include_focus=include_focus)
        except Exception as e:
            errors.append(f"stdio MCP failed: {e}")

        if self.mcp_server_url:
            try:
                return self._fetch_tasks_http(include_focus=include_focus)
            except Exception as e:
                errors.append(f"HTTP MCP bridge failed: {e}")

        raise RuntimeError("; ".join(errors) if errors else "Unable to fetch WorkIQ items.")

    def list_available_tools(self) -> list[str]:
        """Return tool names from WorkIQ stdio MCP after session initialization."""
        self.connect_stdio()
        return self._list_tools()

    def _fetch_tasks_stdio(self, include_focus: bool = True) -> list[Task]:
        self.connect_stdio()

        tool_defs = self._list_tool_defs()
        tool_names = list(tool_defs.keys())
        if not tool_names:
            raise RuntimeError(
                "WorkIQ returned no tools. This is usually an auth/consent scope issue. "
                "Run 'workiq-auth' and ensure tenant permissions are granted."
            )

        # Detect whether granular tools exist or only ask_work_iq is available.
        has_granular = bool(
            self._resolve_tool(tool_names, ["get_action_emails"])
            or self._resolve_tool(tool_names, ["get_upcoming_meetings"])
            or self._resolve_tool(tool_names, ["get_assigned_tasks"])
        )
        ask_tool = self._resolve_tool(tool_names, ["ask_work_iq", "ask"]) or self._resolve_tool_by_keywords(
            tool_names, ["ask", "query"]
        )

        if not has_granular and ask_tool:
            return self._fetch_tasks_via_ask(
                ask_tool, tool_defs.get(ask_tool),
                include_focus=include_focus, tool_names=tool_names,
            )

        return self._fetch_tasks_via_granular(tool_names, include_focus=include_focus)

    def _fetch_tasks_via_ask(
        self,
        ask_tool: str,
        tool_def: dict[str, Any] | None,
        include_focus: bool = True,
        tool_names: list[str] | None = None,
    ) -> list[Task]:
        """Fetch tasks using the ask_work_iq conversational tool."""
        focus_types = ', "FOCUS"' if include_focus else ""
        prompt = (
            f'Return ONLY a JSON array, no prose. Each element must be a JSON object with exactly '
            f'two string fields: "type" (one of: "EMAIL", "MEETING", "TASK"{focus_types}) and '
            f'"title" (a short action phrase, max 10 words, no markdown formatting). '
            f"List my actionable work items for today."
        )

        args = self._build_ask_args(tool_def, prompt)
        call_errors: list[str] = []
        debug_url: str | None = None

        try:
            items = self._call_tool_stdio(ask_tool, args, timeout=120.0)
        except Exception as e:
            call_errors.append(f"{ask_tool}: {e}")
            debug_url = self._fetch_debug_link(tool_names or [])
            items = self._fallback_cli_ask(prompt)

        tasks = self._tasks_from_ask_items(items)
        if tasks:
            return tasks

        if call_errors:
            debug_hint = f" Diagnostic link: {debug_url}" if debug_url else ""
            raise RuntimeError(
                "WorkIQ ask tool calls failed or timed out. "
                "Complete consent/auth with 'workiq-auth' and confirm tenant admin consent. "
                f"Details: {' | '.join(call_errors[:3])}{debug_hint}"
            )

        return []

    def _build_ask_args(self, tool_def: dict[str, Any] | None, question: str) -> dict[str, Any]:
        """Build ask tool args using declared input schema keys when available."""
        if not isinstance(tool_def, dict):
            return {"question": question}

        schema = tool_def.get("inputSchema")
        if not isinstance(schema, dict):
            return {"question": question}

        props = schema.get("properties")
        if not isinstance(props, dict):
            return {"question": question}

        for key in ("question", "query", "prompt", "text", "input"):
            if key in props:
                return {key: question}

        # Fallback to first string-like key.
        for key, value in props.items():
            if isinstance(value, dict) and value.get("type") in ("string", ["string", "null"]):
                return {key: question}

        return {"question": question}

    def _fallback_cli_ask(self, question: str) -> list[dict]:
        """Fallback to workiq ask CLI if MCP tools/call for ask hangs."""
        cmd = [self.mcp_command, *self.mcp_args[:-1], "ask", "-q", question]
        try:
            result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=120)
        except Exception:
            return []

        output = (result.stdout or "").strip()
        if not output:
            return []

        lines = [line.strip("- *\t ") for line in output.splitlines() if line.strip()]
        return [{"text": line} for line in lines]

    def _parse_ask_response(self, blob: str) -> list[dict]:
        """Split a markdown/JSON blob from ask_work_iq into individual item dicts.

        Tries JSON array first (when the model follows the structured prompt).
        Falls back to line-by-line markdown stripping grouped by section headers.
        """
        blob = blob.strip()

        # Attempt 1: JSON array
        # Strip common code-fence wrappers the LLM may add
        json_blob = re.sub(r"^```(?:json)?\s*", "", blob)
        json_blob = re.sub(r"\s*```$", "", json_blob).strip()
        if json_blob.startswith("["):
            try:
                data = json.loads(json_blob)
                if isinstance(data, list):
                    return [i for i in data if isinstance(i, dict)]
            except Exception:
                pass

        # Attempt 2: line-by-line cleanup with section tracking
        current_section: str | None = None
        items: list[dict] = []
        for line in blob.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            # Detect markdown section headers: ## EMAIL, # MEETING, etc.
            header_m = re.match(r"^#+\s*(\w+)", stripped)
            if header_m:
                current_section = header_m.group(1).lower()
                continue
            # Skip non-bullet prose lines when no section context yet
            if not re.match(r"^[-*•]\s+", stripped) and not current_section:
                continue
            # Strip markdown formatting
            text = re.sub(r"^[-*•]\s+", "", stripped)
            text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
            text = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", text)
            text = re.sub(r"`([^`]+)`", r"\1", text).strip()
            if text and len(text) > 3:
                item: dict = {"text": text}
                if current_section:
                    item["section"] = current_section
                items.append(item)
        return items

    def _fetch_debug_link(self, tool_names: list[str]) -> str | None:
        """Call get_debug_link and return the URL if available. Never raises."""
        debug_tool = self._resolve_tool(tool_names, ["get_debug_link"])
        if not debug_tool:
            return None
        try:
            items = self._call_tool_stdio(debug_tool, {}, timeout=15.0)
            for item in items:
                for key in ("url", "link", "debugLink", "debug_link", "text"):
                    val = item.get(key, "")
                    if isinstance(val, str) and val.startswith("http"):
                        return val
        except Exception:
            pass
        return None

    def _tasks_from_ask_items(self, items: list[dict]) -> list[Task]:
        """Convert ask-style items (JSON-structured or free text) into queue tasks."""
        tasks: list[Task] = []
        for i, item in enumerate(items, 1):
            # Prefer structured JSON fields (from JSON-prompt response)
            json_type = str(item.get("type", "")).strip().lower()
            json_title = str(item.get("title", "")).strip()

            # Fall back to text/summary/description field
            raw_text = str(item.get("text") or item.get("summary") or item.get("description") or "").strip()

            # Unwrap JSON-wrapped text (e.g. {"response": "..."})
            if raw_text.startswith("{") and raw_text.endswith("}"):
                try:
                    payload = json.loads(raw_text)
                    if isinstance(payload, dict):
                        raw_text = str(
                            payload.get("response") or payload.get("text")
                            or payload.get("summary") or raw_text
                        ).strip()
                except Exception:
                    pass

            title = json_title or raw_text
            if not title:
                continue

            # Strip residual markdown from the title
            clean_title = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", title)
            clean_title = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", clean_title)
            clean_title = re.sub(r"`([^`]+)`", r"\1", clean_title).strip()

            # Determine task kind: JSON type > section header > regex on text
            section = item.get("section", "").lower()
            if json_type == "email":
                kind, priority = "email", 0
                desc = f"Respond to email: {clean_title}"
            elif json_type == "meeting":
                kind, priority = "meeting", 0
                desc = f"Prepare for meeting: {clean_title}"
            elif json_type == "focus":
                kind, priority = "focus", 5
                desc = f"Focus: {clean_title}"
            elif json_type == "task":
                kind, priority = "task", 0
                desc = clean_title
            elif section in ("email", "inbox"):
                kind, priority = "email", 0
                desc = f"Respond to email: {clean_title}"
            elif section in ("meeting", "calendar"):
                kind, priority = "meeting", 0
                desc = f"Prepare for meeting: {clean_title}"
            elif section in ("focus", "priority"):
                kind, priority = "focus", 5
                desc = f"Focus: {clean_title}"
            elif section in ("task", "tasks"):
                kind, priority = "task", 0
                desc = clean_title
            else:
                lowered = clean_title.lower()
                if re.search(r"\b(email|inbox|reply)\b", lowered):
                    kind, priority = "email", 0
                    desc = f"Respond to email: {clean_title}"
                elif re.search(r"\b(meeting|calendar|prep)\b", lowered):
                    kind, priority = "meeting", 0
                    desc = f"Prepare for meeting: {clean_title}"
                elif re.search(r"\b(focus|priority|urgent|top)\b", lowered):
                    kind, priority = "focus", 5
                    desc = f"Focus: {clean_title}"
                else:
                    kind, priority = "task", 0
                    desc = clean_title

            tasks.append(Task(
                name=f"{kind}-{clean_title[:30] or i}",
                description=desc,
                source="workiq",
                priority=priority,
                metadata={"workiq_type": kind, "workiq_id": item.get("id")},
            ))
        return tasks

    def _fetch_tasks_via_granular(self, tool_names: list[str], include_focus: bool = True) -> list[Task]:
        """Fetch tasks using granular per-category tools."""
        tasks: list[Task] = []
        call_errors: list[str] = []

        def call_tool(name: str | None, args: dict[str, Any] | None = None) -> list[dict]:
            if not name:
                return []
            try:
                return self._call_tool_stdio(name, args=args)
            except Exception as e:
                call_errors.append(f"{name}: {e}")
                return []

        email_tool = self._resolve_tool(tool_names, ["get_action_emails"]) or self._resolve_tool_by_keywords(
            tool_names, ["email", "inbox"]
        )
        for email in call_tool(email_tool):
            tasks.append(Task(
                name=f"email-{email.get('subject', 'untitled')[:25]}",
                description=f"Respond to email: {email.get('subject', '')}. {email.get('summary', '')}",
                source="workiq",
                metadata={"workiq_type": "email", "workiq_id": email.get("id")},
            ))

        meeting_tool = self._resolve_tool(tool_names, ["get_upcoming_meetings"]) or self._resolve_tool_by_keywords(
            tool_names, ["meeting", "calendar"]
        )
        for meeting in call_tool(meeting_tool):
            tasks.append(Task(
                name=f"prep-{meeting.get('title', 'meeting')[:25]}",
                description=f"Prepare for meeting: {meeting.get('title', '')}. {meeting.get('agenda', '')}",
                source="workiq",
                metadata={"workiq_type": "meeting", "workiq_id": meeting.get("id")},
            ))

        assigned_tool = self._resolve_tool(tool_names, ["get_assigned_tasks"]) or self._resolve_tool_by_keywords(
            tool_names, ["assigned", "task", "todo", "planner"]
        )
        for wt in call_tool(assigned_tool):
            tasks.append(Task(
                name=f"task-{wt.get('title', 'item')[:25]}",
                description=wt.get("description", wt.get("title", "")),
                source="workiq",
                metadata={"workiq_type": "task", "workiq_id": wt.get("id")},
            ))

        if include_focus:
            focus_tool = self._resolve_tool(
                tool_names, ["get_focus_recommendations", "get_priority_items"]
            ) or self._resolve_tool_by_keywords(tool_names, ["focus", "priority"])
            for item in call_tool(focus_tool):
                title = item.get("title", item.get("subject", "focus-item"))
                summary = item.get("summary", item.get("reason", ""))
                tasks.append(Task(
                    name=f"focus-{title[:25]}",
                    description=f"Focus recommendation: {title}. {summary}".strip(),
                    source="workiq",
                    priority=5,
                    metadata={"workiq_type": "focus", "workiq_id": item.get("id")},
                ))

        if not tasks and call_errors:
            raise RuntimeError(
                "WorkIQ tool calls failed or timed out. "
                "Complete consent/auth with 'workiq-auth' and confirm tenant admin consent. "
                f"Details: {' | '.join(call_errors[:3])}"
            )

        return tasks

    def _fetch_tasks_http(self, include_focus: bool = True) -> list[Task]:
        if not self._http_client:
            self.connect_http()

        tasks = []

        # Fetch emails needing action
        emails = self._call_tool_http("get_action_emails")
        for email in emails:
            tasks.append(Task(
                name=f"email-{email.get('subject', 'untitled')[:25]}",
                description=f"Respond to email: {email.get('subject', '')}. {email.get('summary', '')}",
                source="workiq",
                metadata={"workiq_type": "email", "workiq_id": email.get("id")},
            ))

        # Fetch calendar prep items
        meetings = self._call_tool_http("get_upcoming_meetings")
        for meeting in meetings:
            tasks.append(Task(
                name=f"prep-{meeting.get('title', 'meeting')[:25]}",
                description=f"Prepare for meeting: {meeting.get('title', '')}. {meeting.get('agenda', '')}",
                source="workiq",
                metadata={"workiq_type": "meeting", "workiq_id": meeting.get("id")},
            ))

        # Fetch assigned tasks
        work_tasks = self._call_tool_http("get_assigned_tasks")
        for wt in work_tasks:
            tasks.append(Task(
                name=f"task-{wt.get('title', 'item')[:25]}",
                description=wt.get("description", wt.get("title", "")),
                source="workiq",
                metadata={"workiq_type": "task", "workiq_id": wt.get("id")},
            ))

        if include_focus:
            focus_items = self._call_tool_http("get_focus_recommendations")
            if not focus_items:
                focus_items = self._call_tool_http("get_priority_items")
            for item in focus_items:
                title = item.get("title", item.get("subject", "focus-item"))
                summary = item.get("summary", item.get("reason", ""))
                tasks.append(Task(
                    name=f"focus-{title[:25]}",
                    description=f"Focus recommendation: {title}. {summary}".strip(),
                    source="workiq",
                    priority=5,
                    metadata={"workiq_type": "focus", "workiq_id": item.get("id")},
                ))

        return tasks

    def _call_tool_http(self, tool_name: str, args: dict[str, Any] | None = None) -> list[dict]:
        """Call a tool on an HTTP MCP bridge."""
        if not self._http_client:
            return []
        try:
            response = self._http_client.post(
                "/mcp/tools/call",
                json={"tool": tool_name, "arguments": args or {}},
            )
            response.raise_for_status()
            result = response.json()
            return self._extract_items(result)
        except Exception:
            return []

    def _list_tool_defs(self) -> dict[str, dict[str, Any]]:
        result = self._request("tools/list", {}, timeout=20.0)
        if not isinstance(result, dict):
            return {}
        tools = result.get("tools", [])
        defs: dict[str, dict[str, Any]] = {}
        for tool in tools:
            if isinstance(tool, dict) and isinstance(tool.get("name"), str):
                defs[tool["name"]] = tool
        return defs

    def _list_tools(self) -> list[str]:
        return list(self._list_tool_defs().keys())

    def _resolve_tool(self, available: list[str], preferred: list[str]) -> str | None:
        for candidate in preferred:
            if candidate in available:
                return candidate
        # Some servers namespace tool names. Try suffix match.
        for candidate in preferred:
            for name in available:
                if name.endswith(f".{candidate}") or name.endswith(f"/{candidate}"):
                    return name
        return None

    def _resolve_tool_by_keywords(self, available: list[str], keywords: list[str]) -> str | None:
        lowered = [(name, name.lower()) for name in available]
        for name, lname in lowered:
            if all(kw.lower() in lname for kw in keywords[:1]):
                return name
        for name, lname in lowered:
            if any(kw.lower() in lname for kw in keywords):
                return name
        return None

    def _call_tool_stdio(
        self, tool_name: str | None, args: dict[str, Any] | None = None, timeout: float = 60.0,
    ) -> list[dict]:
        if not tool_name:
            return []
        result = self._request(
            "tools/call",
            {"name": tool_name, "arguments": args or {}},
            timeout=timeout,
        )
        return self._extract_items(result)

    def _request(self, method: str, params: dict[str, Any], timeout: float = 20.0) -> Any:
        req_id = self._next_id
        self._next_id += 1
        self._send({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
        deadline = time.time() + timeout

        while time.time() < deadline:
            msg = self._recv(timeout=max(0.1, deadline - time.time()))
            if not msg:
                continue
            if msg.get("id") == req_id:
                if "error" in msg:
                    raise RuntimeError(str(msg.get("error")))
                return msg.get("result")
        raise TimeoutError(f"Timed out waiting for MCP response: {method}")

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def _send(self, payload: dict[str, Any]) -> None:
        if not self._proc or not self._proc.stdin:
            raise RuntimeError("WorkIQ MCP stdio process is not running.")
        body = json.dumps(payload).encode("utf-8")
        if self._stdio_mode == "jsonl":
            self._proc.stdin.write(body + b"\n")
        else:
            header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
            self._proc.stdin.write(header + body)
        self._proc.stdin.flush()

    def _recv(self, timeout: float = 20.0) -> dict[str, Any] | None:
        if not self._proc or not self._proc.stdout:
            raise RuntimeError("WorkIQ MCP stdio process is not running.")

        deadline = time.time() + timeout
        fd = self._proc.stdout.fileno()

        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                return None
            ready, _, _ = select.select([fd], [], [], remaining)
            if not ready:
                return None

            line = self._proc.stdout.readline()
            if not line:
                return None

            # JSON-lines mode support.
            stripped = line.strip()
            if stripped.startswith(b"{"):
                try:
                    return json.loads(stripped.decode("utf-8"))
                except Exception:
                    continue

            # Content-Length framing support.
            if not line.lower().startswith(b"content-length:"):
                continue

            headers: dict[str, str] = {}
            while True:
                text = line.decode("utf-8", errors="ignore").strip()
                if text:
                    if ":" in text:
                        k, v = text.split(":", 1)
                        headers[k.strip().lower()] = v.strip()

                remaining = deadline - time.time()
                if remaining <= 0:
                    return None
                ready, _, _ = select.select([fd], [], [], remaining)
                if not ready:
                    return None
                line = self._proc.stdout.readline()
                if not line:
                    return None
                if line in (b"\r\n", b"\n"):
                    break

            length_raw = headers.get("content-length")
            if not length_raw:
                continue
            length = int(length_raw)

            body = b""
            while len(body) < length:
                remaining = deadline - time.time()
                if remaining <= 0:
                    return None
                ready, _, _ = select.select([fd], [], [], remaining)
                if not ready:
                    return None
                chunk = self._proc.stdout.read(length - len(body))
                if not chunk:
                    return None
                body += chunk

            if not body:
                return None
            try:
                return json.loads(body.decode("utf-8"))
            except Exception:
                continue

    def _extract_items(self, payload: Any) -> list[dict]:
        """Normalize common MCP response shapes into a list of dict items."""
        if isinstance(payload, list):
            return [i for i in payload if isinstance(i, dict)]

        if not isinstance(payload, dict):
            return []

        content = payload.get("content")
        if isinstance(content, list):
            items: list[dict] = []
            for part in content:
                if not isinstance(part, dict):
                    continue
                if isinstance(part.get("text"), str):
                    text_val = part["text"]
                    if "\n" in text_val:
                        items.extend(self._parse_ask_response(text_val))
                    else:
                        items.append({"text": text_val})
                if isinstance(part.get("json"), list):
                    items.extend([i for i in part["json"] if isinstance(i, dict)])
                elif isinstance(part.get("json"), dict):
                    items.append(part["json"])
                elif isinstance(part.get("data"), list):
                    items.extend([i for i in part["data"] if isinstance(i, dict)])
            if items:
                return items

        for key in ("items", "result", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [i for i in value if isinstance(i, dict)]
            if isinstance(value, dict):
                return [value]

        return []
