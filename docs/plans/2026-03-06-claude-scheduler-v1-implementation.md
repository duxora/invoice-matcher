# claude-scheduler v1.0 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restructure the prototype into a PyPI-installable package with unified CLI, config file, proper error handling, and documentation.

**Architecture:** Move all code into `src/claude_scheduler/` as a proper Python package. Unify two CLIs into one. Replace hardcoded paths with config file. Add error handling, validation, and docs.

**Tech Stack:** Python 3.10+, FastAPI, Uvicorn, Jinja2, Rich, Textual, TOML config

---

### Task 1: Create package structure and pyproject.toml

Move all source code into `src/claude_scheduler/` package layout. Create pyproject.toml with entry points.

**Files:**
- Create: `src/claude_scheduler/__init__.py`
- Create: `src/claude_scheduler/core/__init__.py`
- Create: `src/claude_scheduler/web/__init__.py`
- Create: `pyproject.toml`
- Move: `claude-scheduler/scheduler/*.py` → `src/claude_scheduler/core/`
- Move: `claude-scheduler/scheduler/console.py` → `src/claude_scheduler/console.py`
- Move: `apps/scheduler/routes.py` → `src/claude_scheduler/web/routes.py`
- Move: `server/main.py` → `src/claude_scheduler/web/app.py`
- Move: `server/templates/` → `src/claude_scheduler/web/templates/`
- Move: `apps/scheduler/templates/` → `src/claude_scheduler/web/templates/scheduler/`
- Move: `server/static/` → `src/claude_scheduler/web/static/`
- Move: `claude-scheduler/tests/` → `tests/`

**Step 1: Create the directory structure**

```bash
mkdir -p src/claude_scheduler/core
mkdir -p src/claude_scheduler/web/templates/scheduler/partials
mkdir -p src/claude_scheduler/web/static/css
```

**Step 2: Move core scheduler modules**

```bash
# Core engine
for f in db.py executor.py models.py orchestrator.py parser.py \
         remediate.py retry.py notify.py isolation.py webhooks.py \
         triggers.py launchd.py monitor.py tui.py; do
    cp claude-scheduler/scheduler/$f src/claude_scheduler/core/$f
done
cp claude-scheduler/scheduler/console.py src/claude_scheduler/console.py
```

**Step 3: Move web files**

```bash
cp server/main.py src/claude_scheduler/web/app.py
cp apps/scheduler/routes.py src/claude_scheduler/web/routes.py
cp server/templates/base.html src/claude_scheduler/web/templates/base.html
cp server/templates/portal.html src/claude_scheduler/web/templates/portal.html
cp apps/scheduler/templates/*.html src/claude_scheduler/web/templates/scheduler/
cp apps/scheduler/templates/partials/*.html src/claude_scheduler/web/templates/scheduler/partials/
cp server/static/css/custom.css src/claude_scheduler/web/static/css/custom.css
```

**Step 4: Move tests**

```bash
cp -r claude-scheduler/tests/ tests/
```

**Step 5: Create `src/claude_scheduler/__init__.py`**

```python
"""claude-scheduler — Scheduled AI tasks for Claude Code."""
__version__ = "1.0.0"
```

**Step 6: Create `src/claude_scheduler/core/__init__.py`**

```python
"""Core scheduler engine."""
```

**Step 7: Create `src/claude_scheduler/web/__init__.py`**

```python
"""Web dashboard for claude-scheduler."""
```

**Step 8: Create `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "claude-scheduler"
version = "1.0.0"
description = "Scheduled AI tasks for Claude Code"
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
authors = [{ name = "Duc Duong" }]
keywords = ["claude", "scheduler", "ai", "automation"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Environment :: Web Environment",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: MacOS",
    "Operating System :: POSIX :: Linux",
    "Programming Language :: Python :: 3",
    "Topic :: Software Development :: Libraries",
]
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "jinja2>=3.1.0",
    "rich>=13.0.0",
    "textual>=0.50.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0", "httpx>=0.27.0"]

[project.scripts]
cs = "claude_scheduler.cli:main"
claude-scheduler = "claude_scheduler.cli:main"

[project.urls]
Homepage = "https://github.com/user/claude-scheduler"
```

**Step 9: Create `LICENSE`**

```
MIT License — standard MIT text
```

**Step 10: Fix all internal imports**

In every file under `src/claude_scheduler/core/`, replace:
- `from .console import ...` → `from claude_scheduler.console import ...`
- `from .db import ...` → `from claude_scheduler.core.db import ...`
- `from .parser import ...` → `from claude_scheduler.core.parser import ...`
- etc.

In `src/claude_scheduler/web/routes.py`, replace:
- `from server.config import ...` → `from claude_scheduler.config import ...`
- `sys.path.insert(0, str(SCHEDULER_DIR))` → remove (now installed as package)
- `from scheduler.db import ...` → `from claude_scheduler.core.db import ...`

In `src/claude_scheduler/web/app.py`, replace:
- `from apps.scheduler.routes import ...` → `from claude_scheduler.web.routes import ...`

In templates, `{% extends "base.html" %}` stays the same (template loader handles it).

**Step 11: Fix template paths**

In `src/claude_scheduler/web/app.py` and `routes.py`, template directories must point to the package:
```python
from pathlib import Path
TEMPLATE_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
```

In routes.py, scheduler templates are now at `templates/scheduler/`:
```python
# Template references change:
# "dashboard.html" → "scheduler/dashboard.html"
# "history.html" → "scheduler/history.html"
# etc.
```

**Step 12: Fix test imports**

In all test files, replace:
- `from scheduler.db import ...` → `from claude_scheduler.core.db import ...`
- `from scheduler.parser import ...` → `from claude_scheduler.core.parser import ...`
- etc.

Fix fixture paths to be relative to test directory.

**Step 13: Install in development mode and verify**

```bash
pip install -e ".[dev]"
python -c "from claude_scheduler import __version__; print(__version__)"
pytest tests/ -v
```

Expected: All 39 tests pass.

**Step 14: Commit**

```bash
git add src/ pyproject.toml LICENSE tests/
git commit -m "feat: restructure into proper Python package with pyproject.toml"
```

---

### Task 2: Config file and `cs init`

Replace all hardcoded paths with a configuration system.

**Files:**
- Create: `src/claude_scheduler/config.py`
- Modify: `src/claude_scheduler/core/orchestrator.py` — use config paths
- Modify: `src/claude_scheduler/web/routes.py` — use config paths
- Modify: `src/claude_scheduler/web/app.py` — use config paths

**Step 1: Create `src/claude_scheduler/config.py`**

```python
"""Configuration loader for claude-scheduler."""
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

CONFIG_DIR = Path(os.environ.get(
    "CS_CONFIG_DIR",
    Path.home() / ".config" / "claude-scheduler"
))
CONFIG_FILE = CONFIG_DIR / "config.toml"

DEFAULT_CONFIG = """\
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
"""

@dataclass
class ServerConfig:
    port: int = 7070
    host: str = "127.0.0.1"

@dataclass
class PathsConfig:
    tasks_dir: Path = field(default_factory=lambda: CONFIG_DIR / "tasks")
    logs_dir: Path = field(default_factory=lambda: CONFIG_DIR / "logs")
    data_dir: Path = field(default_factory=lambda: CONFIG_DIR / "data")

@dataclass
class DefaultsConfig:
    model: str = "claude-sonnet-4-6"
    tools: str = "Read,Grep,Glob"
    max_turns: int = 10
    timeout: int = 300
    retry: int = 1
    on_failure: str = "investigate"

@dataclass
class Config:
    server: ServerConfig = field(default_factory=ServerConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    defaults: DefaultsConfig = field(default_factory=DefaultsConfig)

def _resolve_path(p: str) -> Path:
    """Expand ~ and env vars in path strings."""
    return Path(os.path.expandvars(os.path.expanduser(p)))

def load_config() -> Config:
    """Load config from file, falling back to defaults."""
    cfg = Config()
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "rb") as f:
            data = tomllib.load(f)
        if "server" in data:
            cfg.server.port = data["server"].get("port", cfg.server.port)
            cfg.server.host = data["server"].get("host", cfg.server.host)
        if "paths" in data:
            if "tasks_dir" in data["paths"]:
                cfg.paths.tasks_dir = _resolve_path(data["paths"]["tasks_dir"])
            if "logs_dir" in data["paths"]:
                cfg.paths.logs_dir = _resolve_path(data["paths"]["logs_dir"])
            if "data_dir" in data["paths"]:
                cfg.paths.data_dir = _resolve_path(data["paths"]["data_dir"])
        if "defaults" in data:
            d = data["defaults"]
            cfg.defaults.model = d.get("model", cfg.defaults.model)
            cfg.defaults.tools = d.get("tools", cfg.defaults.tools)
            cfg.defaults.max_turns = d.get("max_turns", cfg.defaults.max_turns)
            cfg.defaults.timeout = d.get("timeout", cfg.defaults.timeout)
            cfg.defaults.retry = d.get("retry", cfg.defaults.retry)
            cfg.defaults.on_failure = d.get("on_failure", cfg.defaults.on_failure)
    return cfg

def init_config():
    """Create config directory and default config file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    cfg.paths.tasks_dir.mkdir(parents=True, exist_ok=True)
    cfg.paths.logs_dir.mkdir(parents=True, exist_ok=True)
    cfg.paths.data_dir.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(DEFAULT_CONFIG)
    return cfg

# Singleton for use across the app
_config: Config | None = None

def get_config() -> Config:
    global _config
    if _config is None:
        _config = load_config()
    return _config
```

**Step 2: Update all modules to use config paths**

Replace hardcoded `TASKS_DIR`, `LOGS_DIR`, `DATA_DIR` in routes.py, app.py, and CLI with `get_config().paths.*`.

**Step 3: Verify tests pass with config**

```bash
pytest tests/ -v
```

**Step 4: Commit**

```bash
git add src/claude_scheduler/config.py
git commit -m "feat: add TOML config file with cs init setup"
```

---

### Task 3: Unified CLI

Merge the `cs` CLI and `tools` CLI into one `cs` command.

**Files:**
- Create: `src/claude_scheduler/cli.py`
- Delete: old `cs` and `tools` files (after migration)

**Step 1: Create `src/claude_scheduler/cli.py`**

Merge all commands from both CLIs into one argparse-based CLI:
- From `cs`: run, run-all, status, history, errors, tickets, remediate, logs, notifications, doctor, dashboard, approvals, approve, reject, artifacts, new, enable, disable
- From `tools`: serve, install (as `serve --install`), uninstall (as `serve --uninstall`)
- New: init, --version

The CLI imports from `claude_scheduler.core.*` and `claude_scheduler.config`.

Key changes from old CLIs:
- `get_db()` uses `get_config().paths.data_dir`
- `TASKS_DIR` = `get_config().paths.tasks_dir`
- `LOGS_DIR` = `get_config().paths.logs_dir`
- `cmd_serve()` starts uvicorn with `get_config().server.port`
- `cmd_init()` calls `init_config()` and prints setup summary

**Step 2: Verify CLI works**

```bash
pip install -e .
cs --version
cs init
cs doctor
cs status
cs serve &
sleep 2
# verify http://localhost:7070 works
kill %1
```

**Step 3: Commit**

```bash
git add src/claude_scheduler/cli.py
git commit -m "feat: unified CLI with serve, init, and all scheduler commands"
```

---

### Task 4: Fix web app for new package structure

Update the web app to work with the new package layout.

**Files:**
- Modify: `src/claude_scheduler/web/app.py`
- Modify: `src/claude_scheduler/web/routes.py`
- Modify: all templates that reference template paths

**Step 1: Update `app.py`**

- Template and static directories use `Path(__file__).parent`
- Register scheduler app with proper imports
- Add error handlers (404, 500)
- Enable OpenAPI docs

**Step 2: Update `routes.py`**

- Remove all `sys.path.insert` hacks
- Import from `claude_scheduler.core.*`
- Import config from `claude_scheduler.config`
- Use `ChoiceLoader` for templates (scheduler/ + base)
- Add try/except to all route handlers
- Template names prefixed with `scheduler/` where needed

**Step 3: Add error page templates**

Create `src/claude_scheduler/web/templates/error.html`:
```html
{% extends "base.html" %}
{% block content %}
<div class="text-center py-16">
    <div class="text-6xl font-bold text-hub-muted mb-4">{{ code }}</div>
    <div class="text-xl mb-2">{{ title }}</div>
    <div class="text-hub-muted mb-6">{{ message }}</div>
    <a href="/" class="btn btn-primary">Back to Home</a>
</div>
{% endblock %}
```

**Step 4: Verify all pages load**

```bash
cs serve &
sleep 2
python3 -c "
import urllib.request
for p in ['/', '/scheduler/', '/scheduler/history', '/scheduler/errors',
          '/scheduler/tickets', '/scheduler/notifications', '/scheduler/doctor',
          '/scheduler/tasks-new', '/scheduler/approvals']:
    resp = urllib.request.urlopen(f'http://localhost:7070{p}')
    print(f'{p} -> {resp.status}')
"
kill %1
```

Expected: All return 200.

**Step 5: Commit**

```bash
git add src/claude_scheduler/web/
git commit -m "feat: update web app for new package structure with error handling"
```

---

### Task 5: Example tasks and input validation

**Files:**
- Create: `examples/daily-code-review.task`
- Create: `examples/weekly-dep-audit.task`
- Create: `examples/log-summarizer.task`
- Modify: `src/claude_scheduler/core/parser.py` — add validation
- Modify: `src/claude_scheduler/web/routes.py` — validate form input

**Step 1: Create 3 example tasks**

Real, working examples with good prompts.

**`examples/daily-code-review.task`:**
```
# name: Daily Code Review
# schedule: daily 09:00
# workdir: ~/workspace/myproject
# model: claude-sonnet-4-6
# tools: Read,Grep,Glob,Bash
# max_turns: 15
# timeout: 600
# retry: 1
# notify: errors
# on_failure: investigate
# enabled: false
---
Review all git commits from the last 24 hours in this repository.

For each commit:
1. Read the changed files using `git diff HEAD~1`
2. Check for security issues (hardcoded secrets, SQL injection, XSS)
3. Check for code quality (error handling, naming, complexity)
4. Check for missing tests

Output a markdown summary with:
- Total commits reviewed
- Issues found (critical/warning/info)
- Recommendations
```

**`examples/weekly-dep-audit.task`:**
```
# name: Weekly Dependency Audit
# schedule: weekly mon 08:00
# workdir: ~/workspace/myproject
# model: claude-sonnet-4-6
# tools: Read,Grep,Glob,Bash
# max_turns: 10
# timeout: 300
# retry: 1
# notify: all
# on_failure: notify
# enabled: false
---
Audit project dependencies for security and freshness.

Steps:
1. Find package files (package.json, requirements.txt, go.mod, pyproject.toml)
2. For each: check if there are known outdated or deprecated packages
3. Look for pinned versions that might have security patches available
4. Check for unused dependencies (imported but not used in code)

Output a markdown report with:
- Dependencies checked
- Outdated packages with current vs latest version
- Security concerns
- Unused dependencies to consider removing
```

**`examples/log-summarizer.task`:**
```
# name: Log Summarizer
# schedule: every 6h
# workdir: ~/workspace/myproject
# model: claude-haiku-4-5-20251001
# tools: Read,Grep,Glob,Bash
# max_turns: 5
# timeout: 120
# retry: 0
# notify: errors
# on_failure: notify
# enabled: false
---
Summarize recent application logs.

1. Read the last 500 lines of log files in ./logs/
2. Identify: errors, warnings, unusual patterns
3. Group by category and frequency
4. Output a brief summary (max 20 lines)
```

**Step 2: Add schedule validation to parser.py**

```python
import re

VALID_SCHEDULES = [
    r'^daily \d{2}:\d{2}$',
    r'^weekly \w+ \d{2}:\d{2}$',
    r'^every \d+[hm]$',
]

def validate_schedule(schedule: str) -> bool:
    return any(re.match(p, schedule) for p in VALID_SCHEDULES)
```

**Step 3: Add form validation in routes create_task**

Validate name (non-empty, slug-safe), schedule (valid format), prompt (non-empty).
Return to form with error messages if invalid.

**Step 4: Commit**

```bash
git add examples/ src/claude_scheduler/core/parser.py src/claude_scheduler/web/routes.py
git commit -m "feat: add example tasks and input validation"
```

---

### Task 6: README and documentation

**Files:**
- Create: `README.md`

**Step 1: Write README.md**

Sections:
1. **Header** — Name, one-line description, badges
2. **Install** — `pip install claude-scheduler` + prerequisites (claude CLI)
3. **Quickstart** — `cs init` → `cs new` → `cs run` → `cs serve` (4 commands)
4. **Task File Format** — Header fields reference, example
5. **CLI Reference** — All commands with one-line descriptions
6. **Web Dashboard** — Screenshot placeholder, URL, features
7. **Configuration** — config.toml reference
8. **Scheduling** — launchd/systemd setup via `cs serve --install`
9. **License** — MIT

Keep it under 200 lines. Concise, scannable.

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with install, quickstart, and reference"
```

---

### Task 7: Cross-platform support and logging

**Files:**
- Create: `src/claude_scheduler/core/platform.py`
- Modify: `src/claude_scheduler/cli.py` — use platform module for install/uninstall

**Step 1: Create `platform.py`**

Auto-detect macOS (launchd) vs Linux (systemd) vs fallback (cron-like message).

```python
import platform
import subprocess
from pathlib import Path

def detect_platform() -> str:
    system = platform.system()
    if system == "Darwin":
        return "launchd"
    elif system == "Linux":
        return "systemd"
    return "unsupported"

def install_service(port: int, cs_path: str):
    plat = detect_platform()
    if plat == "launchd":
        _install_launchd(port, cs_path)
    elif plat == "systemd":
        _install_systemd(port, cs_path)
    else:
        print("Auto-start not supported on this platform.")
        print(f"Run manually: cs serve --port {port}")

def uninstall_service():
    plat = detect_platform()
    if plat == "launchd":
        _uninstall_launchd()
    elif plat == "systemd":
        _uninstall_systemd()

def _install_launchd(port, cs_path):
    # existing launchd logic from tools CLI
    ...

def _uninstall_launchd():
    # existing uninstall logic
    ...

def _install_systemd(port, cs_path):
    unit = f"""[Unit]
Description=Claude Scheduler Web Dashboard
After=network.target

[Service]
Type=simple
ExecStart={cs_path} serve --port {port}
Restart=on-failure

[Install]
WantedBy=default.target
"""
    unit_dir = Path.home() / ".config" / "systemd" / "user"
    unit_dir.mkdir(parents=True, exist_ok=True)
    unit_path = unit_dir / "claude-scheduler.service"
    unit_path.write_text(unit)
    subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", "claude-scheduler"], capture_output=True)
    print(f"Installed: claude-scheduler.service on port {port}")

def _uninstall_systemd():
    subprocess.run(["systemctl", "--user", "disable", "--now", "claude-scheduler"], capture_output=True)
    unit_path = Path.home() / ".config" / "systemd" / "user" / "claude-scheduler.service"
    if unit_path.exists():
        unit_path.unlink()
    print("Removed: claude-scheduler.service")
```

**Step 2: Add structured logging**

In `src/claude_scheduler/core/`, add a logger that writes to `logs_dir/scheduler.log` with rotation. Use Python's built-in `logging` module.

**Step 3: Commit**

```bash
git add src/claude_scheduler/core/platform.py
git commit -m "feat: cross-platform service support (launchd + systemd)"
```

---

### Task 8: Final verification and cleanup

**Step 1: Clean install test**

```bash
pip install -e ".[dev]"
cs --version
cs init
cs doctor
```

**Step 2: Run all tests**

```bash
pytest tests/ -v
```

Expected: All tests pass.

**Step 3: Verify web dashboard**

```bash
cs serve &
sleep 2
# Test all endpoints
python3 -c "
import urllib.request
for p in ['/', '/scheduler/', '/scheduler/history', '/scheduler/errors',
          '/scheduler/tickets', '/scheduler/notifications', '/scheduler/doctor',
          '/scheduler/tasks-new', '/scheduler/approvals']:
    resp = urllib.request.urlopen('http://localhost:7070' + p)
    print(f'{p} -> {resp.status}')
"
kill %1
```

**Step 4: Verify CLI commands**

```bash
cs status
cs history
cs errors
cs doctor
cs new --name "Test Task" --schedule "daily 09:00" --prompt "Say hello"
cs enable test-task
cs disable test-task
```

**Step 5: Remove old files**

```bash
# Remove old CLI entry points (now replaced by package entry points)
# Remove old server/, apps/ directories (now in src/)
# Keep claude-scheduler/ as-is for backward compat temporarily
```

**Step 6: Update .gitignore**

```
__pycache__/
*.pyc
*.pyo
.pytest_cache/
*.egg-info/
dist/
build/
.eggs/
data/
logs/
```

**Step 7: Final commit**

```bash
git add -A
git commit -m "chore: cleanup old files and finalize v1.0 structure"
```

---

## Verification Checklist

1. `pip install -e .` installs cleanly
2. `cs --version` prints `1.0.0`
3. `cs init` creates `~/.config/claude-scheduler/` with config.toml
4. `cs doctor` shows all green
5. `cs new` creates a task interactively
6. `cs serve` starts web dashboard on port 7070
7. All 10 web pages return 200
8. All 39 tests pass
9. `cs serve --install` sets up auto-start (launchd/systemd)
10. Example tasks exist in `examples/`
11. README has install, quickstart, reference
12. No `sys.path.insert` hacks remain
13. No hardcoded paths remain
