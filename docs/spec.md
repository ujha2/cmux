# cmux Product Spec

This spec reflects the current implementation state of cmux as of March 2026.

## Product Summary

cmux is a terminal-first command center for running parallel AI work sessions in tmux while tracking human work in the same queue.

Core value:
- One queue for AI and human tasks
- Skill-guided prompting for consistent outputs
- Lightweight local persistence (no daemon)
- Optional Microsoft WorkIQ ingestion for task signal capture

## Users and Jobs

- PM/IC workflow operator: Queue and launch multiple AI tasks in parallel.
- Individual contributor: Mix AI execution with focused manual work blocks.
- Team lead: Reuse templates/skills for repeatable docs and updates.

## Functional Requirements

### 1) Task Creation and Queueing

- `cmux add <description>` creates an agent task.
- `cmux add --human <description>` creates a human task.
- `cmux add --priority <n>` sets integer priority (`higher = earlier`).
- `cmux add --run` immediately launches the task after creation.
- `cmux start --file <yaml>` loads tasks from YAML and enqueues them.
- `cmux start --preset <name>` expands preset-defined tasks from config.
- `cmux review` interactively recategorizes pending tasks (agent/human).
- `cmux queue --remove <id>` removes a task by exact id.
- `cmux queue --clear` removes completed/cancelled tasks.

### 2) Task Launch and Execution

- `cmux start` launches pending agent tasks sorted by priority.
- `cmux start <index|id ...>` starts selected pending tasks.
- `cmux start --pick` prompts for numbered selection.
- `cmux start --all` launches all pending agent tasks.
- If no pending agent tasks exist, `cmux start` launches interactive backend mode in tmux.
- Human tasks launch a pomodoro timer instead of an AI backend session.

Execution constraints:
- tmux session name is `cmux`.
- max concurrent sessions enforced by `max_parallel_sessions`.
- output path defaults to `./cmux-output/<YYYY-MM-DD>/<task-name>/`.

### 3) Skill and Template Application

- Skills are loaded from built-ins plus user YAML skills in `~/.cmux/skills/`.
- Unspecified task skills are auto-matched from task text.
- Template files from `~/.cmux/templates/` can be injected via skill definition and `template_skill_map`.
- `cmux skills` lists skills; `cmux skills "<text>"` returns scored matches.

### 4) WorkIQ Integration

Setup:
- On first run (missing `~/.cmux/config.yaml`), cmux auto-runs WorkIQ MCP registration.
- Registration writes a command MCP entry named `workiq` into `~/.claude/settings.json` using:
  - command: `npx`
  - args: `-y @microsoft/workiq@latest [--account <hint>] mcp`
- `cmux init` also ensures WorkIQ registration.

Auth flow:
- `cmux workiq-auth` optionally stores `--tenant-id` and `--account` in config.
- It runs `npx -y @microsoft/workiq@latest [--account ...] accept-eula`.
- It probes MCP readiness by listing available tools.
- Browser behavior:
  - opens Entra portal by default,
  - or admin consent URL when `--admin-consent --tenant-id <id>` is provided.

Task pull flow:
- `cmux pull-workiq` prewarms npm package cache, then fetches WorkIQ items.
- Transport strategy:
  - stdio MCP first (official path),
  - HTTP MCP bridge fallback only when `workiq_mcp_server` is configured.
- Fetch strategy:
  - use granular tools when available (`get_action_emails`, `get_upcoming_meetings`, `get_assigned_tasks`, focus tool),
  - fallback to `ask_work_iq` tool parsing when granular tools are not present,
  - fallback to WorkIQ CLI `ask` if ask tool calls stall.
- `--no-focus` skips focus recommendations.
- `--add-all` bypasses interactive selection.
- Imported tasks are deduplicated by `(metadata.workiq_id, metadata.workiq_type)`.

### 5) Monitoring and Operations

- `cmux status` shows pending (numbered) and non-pending tasks with source/priority.
- `cmux panes` shows active tmux pane IDs and backend-derived pane status.
- `cmux logs <index|pane_id>` prints pane output.
- `cmux attach <index|pane_id>` focuses pane/session in tmux.
- `cmux stop [pane_id|all]` stops one pane or all sessions.

### 6) REPL and Dashboard

- Running bare `cmux` enters REPL when no subcommand is given.
- REPL supports add/start/status/stop/review/skills/panes plus WorkIQ commands.
- `cmux dashboard` opens live queue/session view.
- `cmux dashboard --stats` opens SQLite-backed stats views.

## Persistence and Data Model

Primary persisted artifacts:
- `~/.cmux/config.yaml`: runtime config and WorkIQ flags/hints.
- `~/.cmux/queue.json`: task queue state across invocations.
- `~/.claude/settings.json`: MCP registration (`mcpServers.workiq`).
- `~/.cmux/data/history.db`: stats storage (used by dashboard stats panel).

Queue persistence guarantees:
- Mutating queue operations call save immediately.
- Queue is loaded fresh on each command invocation.

## Platform Behavior

- Notifications:
  - macOS via `osascript`
  - Linux via `notify-send`
- URL opening supports native Linux/macOS/Windows and WSL fallbacks (`wslview`, `cmd.exe /c start`).
- Installer supports PEP 668 fallback (`--break-system-packages`) and ships `pyproject.toml` for editable install.

## Current Non-Goals and Known Gaps

- No background daemon or watcher process.
- No automated test suite committed yet.
- Stats recording hooks are not wired into end-of-task lifecycle in current CLI flow.
- Copilot backend interface exists but is not fully implemented for session launch.