"""Cross-platform service installation for claude-scheduler dashboard."""
import os
import platform
import shutil
import subprocess
from pathlib import Path

from claude_scheduler.console import console


def detect_platform() -> str:
    system = platform.system()
    if system == "Darwin":
        return "launchd"
    elif system == "Linux":
        return "systemd"
    return "unsupported"


def install_service(port: int, cs_command: str):
    """Install claude-scheduler as a system service."""
    plat = detect_platform()
    if plat == "launchd":
        _install_launchd(port, cs_command)
    elif plat == "systemd":
        _install_systemd(port, cs_command)
    else:
        console.print("[yellow]Auto-start not supported on this platform.[/yellow]")
        console.print(f"Run manually: [bold]cs serve --port {port}[/bold]")


def uninstall_service():
    """Remove claude-scheduler system service."""
    plat = detect_platform()
    if plat == "launchd":
        _uninstall_launchd()
    elif plat == "systemd":
        _uninstall_systemd()
    else:
        console.print("[yellow]No service to remove on this platform.[/yellow]")


LABEL = "com.claude-scheduler.dashboard"


def _install_launchd(port: int, cs_command: str):
    plist_dir = Path.home() / "Library" / "LaunchAgents"
    plist_dir.mkdir(parents=True, exist_ok=True)
    plist_path = plist_dir / f"{LABEL}.plist"

    # Use python -m for reliability (avoids PATH issues with pip-installed scripts)
    import sys
    python_path = sys.executable

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>-m</string>
        <string>claude_scheduler.cli</string>
        <string>serve</string>
        <string>--port</string>
        <string>{port}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/claude-scheduler.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/claude-scheduler-error.log</string>
</dict>
</plist>"""

    plist_path.write_text(plist_content)
    uid = os.getuid()
    subprocess.run(["launchctl", "bootout", f"gui/{uid}/{LABEL}"], capture_output=True)
    subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", str(plist_path)], capture_output=True)
    console.print(f"[green]Installed:[/green] {LABEL} on port {port}")
    console.print(f"Dashboard: [bold]http://localhost:{port}[/bold]")


def _uninstall_launchd():
    plist_path = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
    uid = os.getuid()
    subprocess.run(["launchctl", "bootout", f"gui/{uid}/{LABEL}"], capture_output=True)
    if plist_path.exists():
        plist_path.unlink()
    console.print(f"[red]Removed:[/red] {LABEL}")


def _install_systemd(port: int, cs_command: str):
    cs_path = shutil.which("cs") or cs_command
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
    console.print(f"[green]Installed:[/green] claude-scheduler.service on port {port}")
    console.print(f"Dashboard: [bold]http://localhost:{port}[/bold]")


def _uninstall_systemd():
    subprocess.run(["systemctl", "--user", "disable", "--now", "claude-scheduler"], capture_output=True)
    unit_path = Path.home() / ".config" / "systemd" / "user" / "claude-scheduler.service"
    if unit_path.exists():
        unit_path.unlink()
    console.print("[red]Removed:[/red] claude-scheduler.service")
