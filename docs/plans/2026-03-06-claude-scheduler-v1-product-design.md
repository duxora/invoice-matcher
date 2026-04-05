# claude-scheduler v1.0 — Product Design

**Date:** 2026-03-06
**Status:** Approved

## Summary

Rework the Tools Hub + Claude Scheduler prototype into a shippable PyPI package for Claude Code power users. Single install (`pip install claude-scheduler`), unified CLI (`cs`), web dashboard, proper configuration.

## Target Audience

Claude Code power users who already have `claude` CLI installed and want to automate recurring tasks (code reviews, audits, summaries, dependency checks).

## Product Identity

- **Name:** claude-scheduler
- **CLI:** `cs` (primary) / `claude-scheduler` (alias)
- **Install:** `pip install claude-scheduler`
- **Port:** 7070 (configurable)
- **Config:** `~/.config/claude-scheduler/config.toml`

## Package Structure

```
claude-scheduler/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/claude_scheduler/
│   ├── __init__.py          # Version string
│   ├── cli.py               # Unified CLI entry point
│   ├── config.py            # Config loader + defaults
│   ├── core/                # Scheduler engine
│   │   ├── __init__.py
│   │   ├── db.py
│   │   ├── executor.py
│   │   ├── models.py
│   │   ├── orchestrator.py
│   │   ├── parser.py
│   │   ├── remediate.py
│   │   ├── retry.py
│   │   ├── notify.py
│   │   ├── isolation.py
│   │   ├── webhooks.py
│   │   ├── triggers.py
│   │   └── platform.py     # launchd/systemd auto-detect
│   ├── web/                 # Web server + dashboard
│   │   ├── __init__.py
│   │   ├── app.py           # FastAPI application
│   │   ├── routes.py        # All routes
│   │   ├── templates/       # All Jinja2 templates
│   │   └── static/          # CSS
│   └── console.py           # Rich CLI output
├── examples/
│   ├── daily-code-review.task
│   ├── weekly-dep-audit.task
│   └── log-summarizer.task
└── tests/
```

## Unified CLI

```bash
# Setup
cs init                        # First-time setup
cs serve                       # Start web dashboard
cs serve --install             # Auto-start on login
cs serve --uninstall           # Remove auto-start

# Task management
cs new                         # Create task (interactive + $EDITOR)
cs new --name X --prompt "..." # Inline creation
cs enable <slug>               # Enable a task
cs disable <slug>              # Disable a task

# Execution
cs run <task-file>             # Run single task
cs run <task-file> --dry-run   # Preview without executing
cs run-all                     # Run all enabled tasks

# Monitoring
cs status                      # Task dashboard
cs history                     # Run history
cs errors                      # Error log
cs tickets                     # Remediation tickets
cs logs <task>                 # View logs
cs doctor                      # Health check
cs notifications               # Notification inbox
cs dashboard                   # TUI dashboard (Textual)

# Approvals
cs approvals                   # List pending
cs approve <id>                # Approve
cs reject <id>                 # Reject
```

## Configuration

File: `~/.config/claude-scheduler/config.toml`

```toml
[server]
port = 7070
host = "127.0.0.1"

[paths]
tasks_dir = "~/.config/claude-scheduler/tasks"
logs_dir = "~/.config/claude-scheduler/logs"
data_dir = "~/.config/claude-scheduler/data"

[defaults]
model = "claude-sonnet-4-6"
tools = "Read,Grep,Glob"
max_turns = 10
timeout = 300
retry = 1
on_failure = "investigate"
```

Created automatically by `cs init`. All paths resolve `~` and `$ENV_VARS`.

## Implementation Priorities

### P0 — Blocking Ship
1. pyproject.toml with entry points (`cs` and `claude-scheduler`)
2. Restructure into src/claude_scheduler/ package
3. Config file loader (replaces all hardcoded paths)
4. README (install, quickstart, task format reference, CLI reference)
5. Error handling in all web routes
6. Input validation (schedule format, task names, paths)
7. 3 working example tasks
8. `cs init` command

### P1 — Expected Quality
9. Error page templates (404, 500)
10. Cross-platform: auto-detect launchd vs systemd
11. Proper logging (file-based, rotated)
12. OpenAPI docs at /docs
13. `cs --version`

### P2 — Polish
14. Empty state UI (no tasks → create first task)
15. Form validation with inline errors
16. Toast notifications for actions
17. Consistent template styling

## What's Cut (YAGNI for v1)
- Multi-user auth (localhost only)
- Docker support
- Homebrew formula
- Windows support
- Prometheus metrics
- Workspace provisioner (separate project)

## Dependencies
- fastapi
- uvicorn[standard]
- jinja2
- rich
- textual
- tomli (Python <3.11) / tomllib (3.11+)

## Non-Goals
- Not a hosted service
- Not multi-tenant
- Not a general task scheduler (specifically for Claude CLI)
