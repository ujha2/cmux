# cmux

cmux is a command center for managing parallel AI sessions alongside your own work.

- Runs AI tasks in tmux panes
- Tracks human tasks with pomodoro timers
- Supports skill-based prompting and template injection
- Registers official @microsoft/workiq MCP by default and pulls WorkIQ signals via stdio MCP (HTTP fallback optional)

## Install

```bash
./install.sh
```

The installer handles platform setup and can recover from PEP 668 managed Python environments.

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

## Documentation

- User guide: docs/user-guide.md
- Architecture: docs/architecture.md