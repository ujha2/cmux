# cmux

cmux is a command center for managing parallel AI sessions alongside your own work.

- Runs AI tasks in tmux panes
- Tracks human tasks with pomodoro timers
- Supports skill-based prompting and template injection
- Registers official @microsoft/workiq MCP by default and pulls WorkIQ signals via stdio MCP (HTTP fallback optional)

Current docs set:
- Product spec: docs/spec.md
- User guide: docs/user-guide.md
- Architecture: docs/architecture.md

## Install

```bash
./install.sh
```

The installer handles platform setup, includes editable install metadata via `pyproject.toml`, and can recover from PEP 668 managed Python environments.

## Quick Start

```bash
cmux workiq-auth
# For tenant admin consent (if required):
cmux workiq-auth --admin-consent --tenant-id <entra-tenant-id>
# If you have multiple cached accounts, optionally pin one:
cmux workiq-auth --account <email-or-account-id>
cmux add "write a PRD for notifications"
cmux pull-workiq
cmux status
cmux start
```

WorkIQ notes:
- `workiq-auth` runs EULA/auth bootstrap and MCP readiness probe.
- `pull-workiq` uses official stdio MCP first, then optional HTTP bridge fallback when configured.
- `pull-workiq` supports interactive selective import, plus `--add-all` and `--no-focus`.

## Documentation

- Spec: [docs/spec.md](docs/spec.md)
- User guide: [docs/user-guide.md](docs/user-guide.md)
- Architecture: [docs/architecture.md](docs/architecture.md)

## User Guide (At A Glance)

### Common Commands

```bash
cmux add "draft weekly status"        # add agent task
cmux add --human "review PR #123"     # add human task
cmux status                           # view queue and task states
cmux start                            # start pending agent tasks
cmux start --pick                     # interactive task picker
cmux panes                            # show active tmux panes
cmux logs 1                           # logs by task index
cmux stop all                         # stop all running sessions
```

### WorkIQ Flow

```bash
cmux workiq-auth
cmux pull-workiq
cmux pull-workiq --add-all
cmux pull-workiq --no-focus
```

### Skills And Templates

```bash
cmux skills
cmux skills "create a roadmap deck"
cmux template list
cmux template create company-context
```

For full workflows, examples, troubleshooting, and configuration details, use the complete guide: [docs/user-guide.md](docs/user-guide.md).
