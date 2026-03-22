# cmux Architecture

Technical reference for contributors and future iteration.

---

## Module Map

```
cmux/
├── backend/        AI execution layer (tmux pane commands)
├── core/           CLI entry, session orchestration, REPL, pomodoro
├── dashboard/      Textual TUI + SQLite stats
├── integrations/   OS-level features (context menus)
├── output/         Format routing (md, docx, pptx)
├── skills/         Skill definitions + auto-matching
├── tasks/          Data models, queue, input sources
└── templates/      Template loading + variable substitution
```

---

## Data Flow

### First-Run Setup Flow

```
First run (no ~/.cmux/config.yaml)
    │
    ▼
load_config() -> defaults
    │
    ▼
_maybe_setup_workiq(config, first_time=True)
    │
    ├─ save_config(config)
    └─ upsert ~/.claude/settings.json mcpServers.workiq
       command: npx
       args: -y @microsoft/workiq@latest [--account <hint>] mcp
    │
    ▼
set config.workiq_registered = true
    │
    ▼
save config
```

### Task Lifecycle

```
                  ┌──────────────┐
                  │   Sources    │
                  │ CLI / YAML / │
                  │  Preset / MCP│
                  └──────┬───────┘
                         │ add()
                         ▼
                  ┌──────────────┐
                  │  TaskQueue   │──── queue.json
                  │  (pending)   │
                  └──────┬───────┘
                         │ start
              ┌──────────┴──────────┐
              ▼                     ▼
      ┌──────────────┐     ┌──────────────┐
      │ Agent Task   │     │ Human Task   │
      │ (tmux pane)  │     │ (pomodoro)   │
      └──────┬───────┘     └──────┬───────┘
             │                     │
             ▼                     ▼
      ┌──────────────┐     ┌──────────────┐
      │  Backend     │     │  Timer       │
      │  (claude)    │     │  (rich Live) │
      └──────┬───────┘     └──────┬───────┘
             │                     │
             ▼                     ▼
      ┌──────────────────────────────────┐
      │          done / error            │
      │     _notify() → OS notification  │
            │  queue persisted in queue.json   │
      └─────────────────────────────────-┘
```

### WorkIQ Auth Flow

```
cmux workiq-auth [--tenant-id] [--account]
    │
    ▼
save_config(workiq_tenant_id/workiq_account)
    │
    ├─ optional browser open
    │   ├─ admin consent URL when --admin-consent + tenant id
    │   └─ Entra portal otherwise
    │
    ├─ run: npx -y @microsoft/workiq@latest [--account] accept-eula
    │
    └─ MCP readiness probe: list_available_tools()
       ├─ success: print detected tools
       └─ failure: guidance to re-run auth/admin consent
```

### WorkIQ Pull Flow

```
cmux pull-workiq
    │
    ▼
load_config()
    │
    ▼
prewarm npm package (npx ... --version)
    │
    ▼
WorkIQSource.fetch_tasks(include_focus=True)
    │
    ├─ stdio MCP (default): npx -y @microsoft/workiq@latest mcp
    └─ HTTP MCP bridge (fallback): workiq_mcp_server when configured
    │
    ├─ granular tools when available
    │   ├─ get_action_emails
    │   ├─ get_upcoming_meetings
    │   ├─ get_assigned_tasks
    │   └─ get_focus_recommendations (fallback get_priority_items)
    └─ else ask_work_iq strategy (CLI ask fallback on call timeout)
    │
    ▼
Interactive review table (or --add-all)
    │
    ▼
TaskQueue.add() with source=workiq + metadata(workiq_id, workiq_type)
    │
    └─ dedupe by (workiq_id, workiq_type)
    │
    ▼
Normal queue/start lifecycle
```

### Queue Persistence

`~/.cmux/queue.json` is the single source of truth for task state. It's a flat JSON array of serialized Task objects. Every mutating operation calls `_save()` immediately.

The queue is loaded fresh on each CLI invocation (`TaskQueue.__init__` → `_load()`). There's no in-memory daemon — cmux is stateless between commands, with the JSON file as the shared state.

A current implementation caveat: `SessionManager` keeps pane→task mapping in memory per invocation. Pane state checks update that in-memory map, but durable lifecycle truth for CLI views still comes from `queue.json`.

### Session Manager ↔ Backend

```
SessionManager                         AIBackend (ABC)
  │                                       │
  ├─ ensure_session()                     │
  │   └─ libtmux: new/get session         │
  │                                       │
  ├─ launch_task(task, prompt, tools)     │
  │   ├─ split_window()                   │
  │   └─ backend.launch_session(pane)  ──►│ send_keys(cmd)
  │                                       │
  ├─ launch_interactive()                 │
  │   └─ backend.launch_interactive()  ──►│ send_keys("claude")
  │                                       │
  ├─ get_active_panes()                   │
  │   └─ backend.check_status(pane)    ──►│ capture_pane → parse
  │                                       │
  └─ stop_task(pane_id)                   │
      └─ backend.stop_session(pane)    ──►│ send_keys(Ctrl+C)
```

The SessionManager owns the tmux session and pane lifecycle. The Backend only knows how to send commands to a pane and interpret its output. This separation means adding a new backend (e.g., Copilot, Cursor) requires only implementing the `AIBackend` interface.

### Skill Matching

```
User input: "create a competitive analysis of Notion vs Coda"
                    │
                    ▼
            SkillRegistry.auto_match()
                    │
          ┌─────────┼──────────┐
          ▼         ▼          ▼
     name match  alias match  keyword match
     (1.0)       (0.95)       (proportional, ≥0.3)
          │         │          │
          └─────────┼──────────┘
                    ▼
            Best match: competitive_research (0.85)
                    │
                    ▼
            Skill.build_prompt(description, templates)
                    │
                    ▼
            Full prompt with templates injected
```

---

## Key Design Decisions

### Why tmux (not subprocess)?

AI CLI tools (Claude Code, Copilot) are interactive terminal programs. They need a real PTY, handle signals, and may prompt for input. Tmux gives us:
- Real PTY per session
- Persistent sessions that survive terminal disconnect
- Built-in pane management users already understand
- Capture/output inspection without interrupting the process

### Why JSON for the queue (not SQLite)?

The queue is small (typically <100 tasks), frequently read in full, and benefits from human readability for debugging. SQLite is used for stats/history where we need aggregation queries.

### Why no daemon?

cmux is invoked per-command. State lives in files (queue.json, config.yaml, history.db). This means:
- No background process to manage/crash
- No port conflicts
- Works naturally in containers/WSL
- Each command gets a fresh view of state

The tradeoff is that completion detection only happens when you run a cmux command (like `status`). A future `cmux watch` command could poll in the background.

### Why Typer + Rich (not Click, not Textual for everything)?

- Typer gives us type-safe CLI args with zero boilerplate
- Rich is already a Typer dependency — free terminal tables, panels, live displays
- Textual is reserved for the dashboard TUI (heavier, full-screen app)
- The REPL uses plain `console.input()` — no dependency on prompt_toolkit

### Why keep install.sh despite pip install -e .?

- Handles cross-platform dependency setup (tmux + PATH + context menus)
- Detects PEP 668 managed Python environments and retries install with `--break-system-packages`
- Initializes `~/.cmux` layout and starter config for first run

---

## Backend Interface

To add a new AI backend, implement `cmux/backend/base.py:AIBackend`:

```python
class AIBackend(ABC):
    @abstractmethod
    def launch_session(self, pane, prompt, tools, output_dir) -> None:
        """Send the command to run an AI session in the pane."""

    @abstractmethod
    def launch_interactive(self, pane) -> None:
        """Open an interactive session (user drives)."""

    @abstractmethod
    def check_status(self, pane) -> SessionStatus:
        """Inspect pane content, return LAUNCHING/RUNNING/DONE/ERROR."""

    @abstractmethod
    def get_output(self, pane) -> str:
        """Capture current pane text."""

    @abstractmethod
    def stop_session(self, pane) -> None:
        """Gracefully stop the session (e.g., Ctrl+C)."""
```

Status detection is heuristic — each backend parses its own output patterns. The Claude backend checks for a `$` prompt (done) or `error`/`fatal` keywords.

---

## Skill Definition Format

Built-in skills are Python objects in `cmux/skills/builtins/`. User skills are YAML:

```yaml
name: my-skill
description: "What this skill does"
prompt_template: |
  You are an expert at X. The user wants: {{task}}

  Output format: ...
output_formats: [md, docx]
tools: [Read, Edit, WebSearch]
template_files: [company-context.md]
time_estimate_manual_minutes: 90
aliases: [my-alias]
keywords: [keyword1, keyword2, keyword3]
```

Skills are loaded from `~/.cmux/skills/` on each registry instantiation. The `template_skill_map` in config allows mapping templates to skills globally.

---

## File Paths

| Path | Purpose |
|------|---------|
| `~/.cmux/config.yaml` | Main configuration |
| `~/.claude/settings.json` | Claude MCP server registry (includes `workiq` entry when configured) |
| `~/.cmux/queue.json` | Task queue (all states) |
| `~/.cmux/data/history.db` | SQLite stats database |
| `~/.cmux/skills/*.yaml` | User-defined skills |
| `~/.cmux/templates/*.md` | Prompt templates |
| `./cmux-output/{date}/{task}/` | Default output directory |
| `~/.cmux/tasks.yaml` | Reserved task source path constant (not auto-loaded by default) |

---

## Error Handling

- **No tmux server:** libtmux raises on connection failure → caught in CLI, user sees "tmux not running"
- **Max sessions reached:** `launch_task()` raises `RuntimeError` → CLI prints error, stops launching
- **Backend not implemented:** `NotImplementedError` from copilot backend → shown to user
- **Corrupt queue.json:** `_load()` catches all exceptions → starts with empty queue
- **Missing config:** `load_config()` returns defaults → auto-init creates file
- **WorkIQ MCP/tool timeout:** `pull-workiq` has heartbeat + timeout messages and explicit auth/consent remediation hints

---

## Testing Strategy

Not yet implemented. Recommended approach:

- **Unit tests:** Task model creation, queue add/remove/find/priority sorting, skill matching scores
- **Integration tests:** CLI commands via `typer.testing.CliRunner` (no tmux needed for add/status/queue)
- **Tmux tests:** Require a running tmux server — test session creation, pane splitting, backend command sending
- **Snapshot tests:** Status table output, skill list output
