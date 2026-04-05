"""Generate and manage macOS launchd plist files."""
import re, os, subprocess
from pathlib import Path
from .models import Task
from .parser import find_tasks
from claude_scheduler.console import console

DAY_MAP = {"mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 0}

def schedule_to_plist_xml(schedule: str) -> str:
    m = re.match(r'^daily (\d{2}):(\d{2})$', schedule)
    if m:
        return (f"    <key>StartCalendarInterval</key>\n    <dict>\n"
                f"        <key>Hour</key><integer>{int(m[1])}</integer>\n"
                f"        <key>Minute</key><integer>{int(m[2])}</integer>\n"
                f"    </dict>")

    m = re.match(r'^weekly (\w+) (\d{2}):(\d{2})$', schedule)
    if m:
        wd = DAY_MAP.get(m[1], 1)
        return (f"    <key>StartCalendarInterval</key>\n    <dict>\n"
                f"        <key>Weekday</key><integer>{wd}</integer>\n"
                f"        <key>Hour</key><integer>{int(m[2])}</integer>\n"
                f"        <key>Minute</key><integer>{int(m[3])}</integer>\n"
                f"    </dict>")

    m = re.match(r'^every (\d+)h$', schedule)
    if m:
        return f"    <key>StartInterval</key>\n    <integer>{int(m[1])*3600}</integer>"

    m = re.match(r'^every (\d+)m$', schedule)
    if m:
        return f"    <key>StartInterval</key>\n    <integer>{int(m[1])*60}</integer>"

    raise ValueError(f"Unsupported schedule: {schedule}")

PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/zsh</string>
        <string>-l</string>
        <string>-c</string>
        <string>{cs_path} run {task_file}</string>
    </array>
{interval_xml}
    <key>StandardOutPath</key>
    <string>{log_out}</string>
    <key>StandardErrorPath</key>
    <string>{log_err}</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>"""

def install(tasks_dir: Path, logs_dir: Path, cs_path: str,
            launchd_dir: Path = None, dry_run: bool = False):
    launchd_dir = launchd_dir or Path.home() / "Library" / "LaunchAgents"
    launchd_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    uid = os.getuid()

    tasks = [t for t in find_tasks(tasks_dir) if t.enabled]
    for task in tasks:
        label = f"com.claude-scheduler.{task.slug}"
        plist_path = launchd_dir / f"{label}.plist"
        if task.trigger == "file_watch" and task.watch_paths:
            from .triggers import expand_watch_paths
            paths = expand_watch_paths(task.watch_paths)
            interval_xml = "    <key>WatchPaths</key>\n    <array>\n"
            for p in paths:
                interval_xml += f"        <string>{p}</string>\n"
            interval_xml += "    </array>"
        else:
            try:
                interval_xml = schedule_to_plist_xml(task.schedule)
            except ValueError as e:
                console.print(f"[yellow]Skipping {task.name}: {e}[/yellow]")
                continue

        content = PLIST_TEMPLATE.format(
            label=label, cs_path=cs_path,
            task_file=str(task.file_path.resolve()),
            interval_xml=interval_xml,
            log_out=str(logs_dir / f"{task.slug}-launchd.log"),
            log_err=str(logs_dir / f"{task.slug}-launchd-error.log"))

        plist_path.write_text(content)
        console.print(f"[green]Generated:[/green] {plist_path}")

        if not dry_run:
            subprocess.run(["launchctl", "bootout", f"gui/{uid}/{label}"],
                           capture_output=True)
            subprocess.run(["launchctl", "bootstrap", f"gui/{uid}",
                           str(plist_path)], capture_output=True)
            console.print(f"[green]Loaded:[/green] {label}")

    console.print(f"\n[bold]{len(tasks)}[/bold] agent(s) installed.")

def uninstall(launchd_dir: Path = None):
    launchd_dir = launchd_dir or Path.home() / "Library" / "LaunchAgents"
    uid = os.getuid()
    for plist in launchd_dir.glob("com.claude-scheduler.*.plist"):
        label = plist.stem
        subprocess.run(["launchctl", "bootout", f"gui/{uid}/{label}"],
                       capture_output=True)
        plist.unlink()
        console.print(f"[red]Removed:[/red] {label}")
