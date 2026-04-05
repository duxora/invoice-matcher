"""Telegram Bridge web routes — status, logs, plugin management."""

import importlib
import pkgutil
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from jinja2 import ChoiceLoader, FileSystemLoader

router = APIRouter()

SERVER_TEMPLATES = Path(__file__).parent.parent.parent / "server" / "templates"
APP_TEMPLATES = Path(__file__).parent / "templates"

_loader = ChoiceLoader([
    FileSystemLoader(str(APP_TEMPLATES)),
    FileSystemLoader(str(SERVER_TEMPLATES)),
])
templates = Jinja2Templates(directory=str(APP_TEMPLATES))
templates.env.loader = _loader

BRIDGE_DIR = Path.home() / "workspace" / "tools" / "telegram-bridge"
LOG_FILE = Path.home() / ".local" / "log" / "telegram-bridge.err"
PLIST_LABEL = "com.ducduong.telegram-bridge"
HOME_DIR = str(Path.home())


def app_context(request: Request, **kwargs):
    """Build template context with sidebar navigation data."""
    from claude_scheduler.web.app import APPS
    return {"request": request, "apps": APPS, **kwargs}


def _is_running() -> bool:
    try:
        result = subprocess.run(
            ["launchctl", "list", PLIST_LABEL],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def _get_plugins_info() -> list[dict]:
    """Discover plugins and their registered commands by inspecting source files."""
    plugins_dir = BRIDGE_DIR / "src" / "telegram_bridge" / "plugins"
    plugins = []

    # Parse each plugin file to find registered commands
    for f in sorted(plugins_dir.glob("*.py")):
        if f.name == "__init__.py":
            continue

        commands = []
        content = f.read_text()
        # Extract commands from reg.register() calls
        for line in content.splitlines():
            line = line.strip()
            if "reg.register(" in line or "registry.register(" in line:
                # Extract the command name
                try:
                    cmd = line.split('"')[1]
                    commands.append(cmd)
                except (IndexError, ValueError):
                    pass

        plugins.append({
            "name": f.stem,
            "path": str(f),
            "commands": commands,
        })

    return plugins


def _get_all_commands() -> list[dict]:
    """Get all commands from all plugins."""
    commands = [
        {"name": "/help", "plugin": "system", "description": "Show all commands"},
        {"name": "/start", "plugin": "system", "description": "Welcome message"},
        {"name": "/ping", "plugin": "system", "description": "Check bot is alive"},
    ]

    plugins_dir = BRIDGE_DIR / "src" / "telegram_bridge" / "plugins"
    for f in sorted(plugins_dir.glob("*.py")):
        if f.name == "__init__.py":
            continue
        content = f.read_text()
        for line in content.splitlines():
            line = line.strip()
            if "reg.register(" in line:
                try:
                    parts = line.split('"')
                    cmd_name = parts[1]
                    # Find description
                    desc = ""
                    if "description=" in line:
                        desc_start = line.index('description="') + len('description="')
                        desc_end = line.index('"', desc_start)
                        desc = line[desc_start:desc_end]
                    plugin = f.stem
                    if "plugin=" in line:
                        p_start = line.index('plugin="') + len('plugin="')
                        p_end = line.index('"', p_start)
                        plugin = line[p_start:p_end]
                    commands.append({"name": cmd_name, "plugin": plugin, "description": desc})
                except (IndexError, ValueError):
                    pass

    return commands


def _get_logs(lines: int = 50) -> str:
    if LOG_FILE.exists():
        all_lines = LOG_FILE.read_text().splitlines()
        return "\n".join(all_lines[-lines:])
    return "No log file found."


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    running = _is_running()
    plugins = _get_plugins_info()
    all_commands = _get_all_commands()
    logs = _get_logs(50)
    total_commands = len(all_commands)

    return templates.TemplateResponse("dashboard.html", app_context(
        request,
        running=running,
        plugins=plugins,
        all_commands=all_commands,
        total_commands=total_commands,
        logs=logs,
        home_dir=HOME_DIR,
    ))


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

@router.post("/restart", response_class=HTMLResponse)
async def restart():
    subprocess.run(["launchctl", "stop", PLIST_LABEL], timeout=5)
    subprocess.run(["launchctl", "start", PLIST_LABEL], timeout=5)
    return HTMLResponse('<p class="text-green-400 text-sm">✅ Bot restarted.</p>')


# ---------------------------------------------------------------------------
# HTMX Partials
# ---------------------------------------------------------------------------

@router.get("/partials/status", response_class=HTMLResponse)
async def status_partial():
    running = _is_running()
    color = "text-green-400" if running else "text-red-400"
    label = "Running" if running else "Stopped"
    return HTMLResponse(f'<div class="text-2xl font-bold {color}">{label}</div>')


@router.get("/partials/logs", response_class=HTMLResponse)
async def logs_partial():
    logs = _get_logs(50)
    return HTMLResponse(
        f'<pre class="text-xs text-hub-muted bg-hub-bg rounded p-3 overflow-x-auto max-h-80 overflow-y-auto">{logs}</pre>'
    )


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@router.get("/health")
async def health():
    return {"running": _is_running(), "service": PLIST_LABEL}
