# cmux User Guide

cmux is a command center for managing parallel AI sessions alongside your own work. It runs AI tasks in tmux panes, tracks human tasks with pomodoro timers, and gives you a single view of everything in flight.

---

## Installation

```bash
# Clone and install (recommended)
cd /path/to/cmux
./install.sh

# Verify
cmux --help
```

Manual install (advanced):

```bash
pip install -e .
```

If your distro Python is PEP 668 externally managed (common on Ubuntu/WSL), use:

```bash
pip install --break-system-packages -e .
```

**Requirements:**
- Python 3.9+
- tmux (for AI sessions)
- Claude Code CLI (default backend)

cmux auto-initializes on first run — no `cmux init` needed (though it's available if you want to reset).

---

## Quick Start

```bash
# Add some tasks
cmux add "write a PRD for the notifications feature"
cmux add "competitive analysis of Slack vs Teams vs Discord"
cmux add --human "review the Q1 design doc"

# See what's queued
cmux status

# Launch everything
cmux start
```

That's it. Agent tasks launch in tmux panes. The human task waits for you to start it explicitly.

---

## Adding Tasks

### Basic

```bash
cmux add "research API pricing for our competitors"
```

Creates an agent task (🤖). cmux auto-matches it to the best skill (e.g., `competitive_research`).

### Human tasks

```bash
cmux add --human "review the design doc from Sarah"
```

Human tasks (👤) don't launch an AI session. When you start them, they run a pomodoro timer.

### Priority

```bash
cmux add --priority 5 "urgent: draft the board update"
cmux add --priority 1 "nice to have: clean up templates"
```

Higher number = higher priority. Tasks are sorted by priority in status and start order.

### With a specific skill

```bash
cmux add --skill deck "Q2 planning presentation"
```

### Add and run immediately

```bash
cmux add --run "summarize yesterday's meeting notes"
```

---

## Starting Tasks

### Start all pending agent tasks

```bash
cmux start
```

If no pending tasks exist, this opens an interactive Claude session in tmux.

### Start by number

```bash
cmux status          # see numbered list
cmux start 1         # start task #1
cmux start 1 3 5     # start multiple
```

Numbers correspond to the `#` column in `cmux status`.

### Start by task ID

```bash
cmux start d9473b0e    # full ID
cmux start d947        # prefix match works too
```

### Interactive picker

```bash
cmux start --pick
```

Shows the pending list, then prompts you to enter numbers.

### Start all agent tasks

```bash
cmux start --all
```

### Start a human task

```bash
cmux start 2    # if task #2 is a human task
```

This starts a 25-minute pomodoro timer with a live countdown. Press Ctrl+C to stop early.

### From a preset

```bash
cmux start --preset morning
```

Presets are defined in `~/.cmux/config.yaml`.

### From a YAML file

```bash
cmux start --file sprint-tasks.yaml
```

YAML format:
```yaml
- Write PRD for auth feature
- description: Competitive analysis
  skill: competitive_research
- name: deck-prep
  description: Create Q2 planning deck
  skill: deck
```

---

## Monitoring

### Task status

```bash
cmux status
```

```
          Task Queue
 #  Type  ID        Task                    Skill                Status      Pri  Source
 #1  🤖   a1b2c3d4  research-competitors    competitive_research ⏳ pending  3    interactive
 #2  👤   e5f6g7h8  review-design-doc       —                    ⏳ pending       interactive
     🤖   i9j0k1l2  write-prd               prd_spec             🔄 running       interactive
     🤖   m3n4o5p6  summarize-notes         status_update        ✅ done          yaml
```

Pending tasks get `#` numbers. Running/done tasks don't (they can't be started again).

### Active tmux panes

```bash
cmux panes
```

Shows pane IDs, associated tasks, and their status (launching/running/done/error).

### View session output

```bash
cmux logs 1          # by task index
cmux logs %3         # by tmux pane ID
```

### Attach to a session

```bash
cmux attach 1        # by task index
cmux attach %3       # by pane ID
```

Or go directly to tmux:
```bash
tmux attach -t cmux
```

---

## Managing Tasks

### Review and recategorize

```bash
cmux review
```

Walks through each pending task and asks: agent, human, or skip?

### Remove a task

```bash
cmux queue --remove a1b2c3d4
```

### Clear completed tasks

```bash
cmux queue --clear
```

### Stop sessions

```bash
cmux stop           # stop all
cmux stop %3        # stop specific pane
```

---

## Skills

### List all skills

```bash
cmux skills
```

```
 Skill                 Description                              Outputs    Manual Time
 one_pager             1-page executive summary                 md, docx   ~90m
 prd_spec              Product requirements document            md, docx   ~180m
 deck                  Presentation slides                      pptx       ~120m
 competitive_research  Market & competitor analysis              md         ~150m
 prototype             Working prototype                        code       ~240m
 data_analysis         Data analysis with charts                md, images ~120m
 status_update         Weekly status report                     md, email  ~45m
 brainstorm_reflect    Document review & critique               md         ~60m
 copywriting           Marketing copy                           md         ~90m
 golden_set            Test dataset generation                  csv, json  ~120m
```

### Match a description to skills

```bash
cmux skills "create a slide deck about our product roadmap"
```

Shows skills ranked by match score.

### Create custom skills

Add a YAML file to `~/.cmux/skills/`:

```yaml
# ~/.cmux/skills/weekly-metrics.yaml
name: weekly-metrics
description: "Pull and summarize weekly product metrics"
prompt_template: |
  You are a data analyst. The user needs: {{task}}

  Pull the relevant metrics, create charts, and write a 1-page summary
  with key trends and action items.
output_formats: [md, images]
tools: [Read, WebSearch]
time_estimate_manual_minutes: 60
aliases: [metrics, weekly-report]
keywords: [metrics, analytics, dashboard, weekly, KPI]
```

---

## Templates

Templates are markdown files that get injected into skill prompts.

```bash
cmux template list                    # list templates
cmux template create company-context  # create new
cmux template edit company-context    # edit in $EDITOR
cmux template show company-context    # display
```

Map templates to skills in config:
```yaml
template_skill_map:
  company-context:
    - one_pager
    - prd_spec
    - deck
```

Templates support variables: `{{date}}`, `{{year}}`, `{{quarter}}`, `{{month}}`, `{{week}}`.

---

## Interactive REPL

Run bare `cmux` to enter the REPL:

```
┌ cmux — PM Command Center ┐
└───────────────────────────┘
#1 🤖 research-competitors    p3
#2 👤 review-design-doc
Type 'help' for commands, 'quit' to exit.

cmux> add "draft the weekly update"
  Auto-matched skill: status_update
+ Added: 🤖 draft-the-weekly-update (id: f1e2d3c4)

cmux> start 1
▶ Launched: research-competitors (pane %5)

cmux> status
...

cmux> quit
```

All the same commands work inside the REPL without the `cmux` prefix.

---

## Dashboard

```bash
cmux dashboard          # live sessions view
cmux dashboard --stats  # stats view (tokens, cost, time saved)
```

The dashboard is a full-screen TUI (Textual). Keybindings:
- `r` — refresh
- `s` — toggle between live/stats view
- `q` — quit

---

## Configuration

`~/.cmux/config.yaml`:

```yaml
# AI backend
backend:
  backend: claude                    # claude or copilot
  claude_model: claude-sonnet-4-6    # model for AI tasks
  claude_args: []                    # extra CLI flags

# Session limits
max_parallel_sessions: 5

# Output location
output_dir: ./cmux-output

# Presets (named task batches)
presets:
  morning:
    name: morning
    description: "Daily kickoff"
    tasks:
      - name: standup-prep
        description: "Summarize yesterday's PRs and today's calendar"
        skill: status_update

# Dashboard
dashboard:
  time_saved_multiplier:
    one_pager: 1.5        # multiply manual time estimate

# Template → skill mapping
template_skill_map:
  company-context: [one_pager, prd_spec]
```

---

## Notifications

cmux sends native desktop notifications when tasks complete:
- **macOS:** uses `osascript` (display notification)
- **Linux:** uses `notify-send`

Notifications fire automatically when cmux checks pane status (during `status`, `panes`, or any command that calls `get_active_panes()`).

---

## Microsoft WorkIQ Integration

cmux can pull your Microsoft WorkIQ task signals (assigned tasks, important emails/messages, meeting prep, and focus recommendations) and turn them into queue items.

### First-time setup

On first run (`cmux` with no existing config), cmux automatically configures WorkIQ MCP.

It:
- registers an MCP server named `workiq` in `~/.claude/settings.json`
  using command transport (`npx -y @microsoft/workiq@latest mcp`)

This matches the official `@microsoft/workiq` MCP setup model (local stdio server), not a remote URL.

Most users do not need to set tenant or account manually. WorkIQ uses your interactive login context.
Use `--account` only if you have multiple cached accounts and need to force one.
Use `--tenant-id` only to build/open the admin-consent URL for tenant admins.

You can also run setup later with:

```bash
cmux init
```

### Pull and review WorkIQ items

```bash
cmux pull-workiq
```

`pull-workiq` talks directly to official `@microsoft/workiq` over stdio MCP.
If `workiq_mcp_server` is set, cmux uses that only as a fallback bridge path.

This fetches WorkIQ items and shows a numbered review table so you can choose exactly what to import.

By default cmux fetches:
- action emails
- upcoming meeting prep items
- assigned tasks
- focus recommendations

Selection prompt examples:
- `1 3 5` → add specific items
- `all` → add all fetched items
- empty Enter → cancel

### Add everything automatically

```bash
cmux pull-workiq --add-all
```

### Only assigned/tasks/email/meeting signals (skip focus recommendations)

```bash
cmux pull-workiq --no-focus
```

Imported WorkIQ tasks are tagged with source metadata and deduplicated by WorkIQ item id.

### Auth and scope bootstrap

```bash
cmux workiq-auth
```

This runs WorkIQ consent/auth setup and a probe query so `pull-workiq` can access tenant data.
It also opens Microsoft Entra in your browser by default to help complete sign-in/consent.
The probe validates MCP readiness by listing available WorkIQ tools (it does not wait on a long ask response).

Tenant/account scoped example:

```bash
cmux workiq-auth --account <email-or-account-id>
```

Tenant admin consent best-practice flow:

```bash
cmux workiq-auth --admin-consent --tenant-id <entra-tenant-id>
```

This opens the Microsoft admin-consent URL for the WorkIQ app so a tenant admin can grant organization-wide consent.

---

## tmux Tips

cmux creates a tmux session named `cmux`. Useful commands:

```bash
tmux attach -t cmux            # attach to cmux session
tmux list-panes -t cmux        # see all panes
Ctrl+B d                       # detach (inside tmux)
Ctrl+B [                       # scroll mode (inside tmux)
Ctrl+B o                       # cycle panes
Ctrl+B z                       # zoom/unzoom current pane
```

---

## Workflow Examples

### Morning kickoff

```bash
cmux add --priority 3 "summarize overnight Slack messages"
cmux add --priority 2 "draft standup update from yesterday's git log"
cmux add --human --priority 1 "review PR #847"
cmux start --all    # launches agent tasks
cmux start 3        # start your review when ready
```

### Sprint planning

```bash
cmux start --file sprint-12-tasks.yaml
cmux status         # monitor progress
cmux dashboard      # full TUI view
```

### Quick one-off

```bash
cmux add --run "write a 1-pager on the new auth approach"
```

### Iterative work

```bash
cmux                # enter REPL
cmux> add "analyze churn data from last quarter"
cmux> start 1
cmux> status        # check on it
cmux> logs 1        # see what it's writing
cmux> add --human "review the analysis output"
cmux> start 2       # pomodoro time
```

---

## Troubleshooting

**"No tmux server running"** — Start tmux first: `tmux new -d -s scratch` or just `tmux`.

**"Max parallel sessions reached"** — Increase `max_parallel_sessions` in config or stop existing sessions with `cmux stop`.

**Tasks not persisting** — Check `~/.cmux/queue.json` exists and is valid JSON. Run `cmux init` to reset.

**Skill not matching** — Use `cmux skills "your description"` to see match scores. Add keywords to custom skills for better matching.

**Pane shows as LAUNCHING forever** — The backend detects status by parsing pane output. If Claude hasn't started writing yet, it shows as launching. Wait a moment and re-check with `cmux panes`.

**Installer stops with PEP 668/external managed error** — Re-run `./install.sh`. The installer now detects this case and retries with `--break-system-packages` automatically.

**Installer says no setup.py or pyproject.toml** — Ensure you're on the repository root and pull the latest changes. cmux now ships `pyproject.toml` for editable installs.

**Need to use an HTTP MCP relay anyway** — Set `workiq_mcp_server` in `~/.cmux/config.yaml`. cmux now uses stdio first and HTTP as fallback when configured.
**pull-workiq fails before returning items** — Ensure Node.js is installed and `npx -y @microsoft/workiq@latest mcp` works on your machine, then run `workiq accept-eula` if prompted by WorkIQ first-use requirements.
**pull-workiq returns no items** — Run `cmux workiq-auth` and verify tenant/admin consent has been granted for your Microsoft 365 tenant.
