"""Notification system — macOS alerts + persistent SQLite log."""
import shutil
import subprocess
from .db import Database

_HAS_TERMINAL_NOTIFIER = shutil.which("terminal-notifier") is not None

SOUNDS = {
    "info": "Glass",
    "warning": "Purr",
    "error": "Basso",
    "action": "Sosumi",
}

def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')

def _send_desktop(title: str, message: str, severity: str = "info",
                  action_cmd: str = ""):
    sound = SOUNDS.get(severity, "default")

    if _HAS_TERMINAL_NOTIFIER:
        cmd = [
            "terminal-notifier",
            "-title", title,
            "-message", message,
            "-sound", sound,
            "-group", "claude-scheduler",
            "-sender", "com.apple.Terminal",
        ]
        if action_cmd:
            cmd.extend(["-execute", action_cmd])
        subprocess.run(cmd, capture_output=True, timeout=5)
    else:
        script = (
            f'display notification "{_escape(message)}"'
            f' with title "{_escape(title)}"'
            f' sound name "{sound}"'
        )
        subprocess.run(["osascript", "-e", script],
                       capture_output=True, timeout=5)

def _log_notification(db: Database | None, task_name: str, severity: str,
                      title: str, message: str, action_cmd: str = ""):
    if db is None:
        return
    from datetime import datetime, timezone
    db.execute(
        "INSERT INTO notifications"
        " (task_name, severity, title, message, sent_at, action_cmd)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (task_name, severity, title, message,
         datetime.now(timezone.utc).isoformat(), action_cmd))
    db.conn.commit()

def notify_error(task_name: str, error_message: str,
                 attempt: int = 1, db: Database = None):
    title = "Claude Scheduler — Task Failed"
    msg = f"{task_name} (attempt {attempt}): {error_message[:100]}"
    action = f"./cs errors --task '{task_name}'"
    _send_desktop(title, msg, "error", action)
    _log_notification(db, task_name, "error", title, msg, action)

def notify_success(task_name: str, db: Database = None):
    title = "Claude Scheduler"
    msg = f"{task_name} completed successfully"
    _send_desktop(title, msg, "info")
    _log_notification(db, task_name, "info", title, msg)

def notify_ticket(task_name: str, ticket_id: int, db: Database = None):
    title = "Claude Scheduler — Action Needed"
    msg = (f"{task_name}: ticket #{ticket_id} needs your input")
    action = f"./cs remediate {ticket_id}"
    _send_desktop(title, msg, "action", action)
    _log_notification(db, task_name, "action", title, msg, action)
