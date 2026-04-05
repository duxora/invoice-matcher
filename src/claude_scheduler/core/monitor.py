"""Display functions for status, history, errors, tickets."""
from .db import Database
from .parser import find_tasks
from claude_scheduler.console import (
    console, STATUS_COLORS, TICKET_COLORS,
    SEVERITY_COLORS, SEVERITY_ICONS, DOCTOR_OK, DOCTOR_FAIL,
)
from pathlib import Path
from rich.table import Table
from rich.panel import Panel


def show_status(db: Database, tasks_dir: Path):
    tasks = find_tasks(tasks_dir)
    states = {s["task_name"]: s for s in db.get_all_task_states()}

    table = Table(title="Task Status")
    table.add_column("Task", style="bold")
    table.add_column("Schedule")
    table.add_column("Last Status")
    table.add_column("Failures", justify="right")
    table.add_column("Total Runs", justify="right")

    for task in tasks:
        s = states.get(task.name, {})
        status = s.get("last_status", "never")
        consec = s.get("consecutive_failures", 0)
        total = s.get("total_runs", 0)
        color = STATUS_COLORS.get(status, "")
        status_text = f"[{color}]{status}[/{color}]" if color else status
        fail_text = f"{consec}"
        if consec >= 3:
            fail_text = f"[red]{consec} ![/red]"
        table.add_row(
            task.name, task.schedule, status_text,
            fail_text, str(total),
        )

    console.print(table)

    # Summary row
    total_tasks = len(tasks)
    healthy = sum(1 for t in tasks if states.get(t.name, {}).get("last_status") == "success")
    failing = sum(1 for t in tasks if states.get(t.name, {}).get("consecutive_failures", 0) > 0)
    all_count = len(list(Path(tasks_dir).glob("*.task")))
    disabled = all_count - total_tasks
    cost_row = db.execute(
        "SELECT COALESCE(SUM(cost_usd), 0) FROM task_runs"
        " WHERE started_at > datetime('now', '-30 days')").fetchone()
    cost_30d = cost_row[0] if cost_row else 0
    console.print(
        f"\nTotal: {total_tasks} tasks | "
        f"[green]{healthy} healthy[/green] | "
        f"[red]{failing} failing[/red] | "
        f"[dim]{disabled} disabled[/dim] | "
        f"${cost_30d:.2f}/30d"
    )


def show_history(db: Database, task_name: str = None, limit: int = 20):
    runs = db.get_run_history(task_name, limit)
    if not runs:
        console.print("[dim]No run history found.[/dim]")
        return

    table = Table(title="Run History")
    table.add_column("ID", justify="right")
    table.add_column("Task", style="bold")
    table.add_column("Status")
    table.add_column("Duration", justify="right")
    table.add_column("Attempt", justify="right")
    table.add_column("Started")

    for r in runs:
        dur = f"{r.duration_seconds:.1f}s" if r.duration_seconds else "-"
        started = r.started_at[:19] if r.started_at else "-"
        color = STATUS_COLORS.get(r.status, "")
        status_text = f"[{color}]{r.status}[/{color}]" if color else r.status
        table.add_row(
            str(r.id), r.task_name, status_text,
            dur, str(r.attempt), started,
        )

    console.print(table)


ERROR_TYPE_COLORS = {
    "timeout": "yellow",
    "crash": "magenta",
    "exit_code": "red",
}


def show_errors(db: Database, task_name: str = None, limit: int = 20):
    errors = db.get_errors(task_name, limit)
    if not errors:
        console.print("[dim]No errors found.[/dim]")
        return

    table = Table(title="Errors")
    table.add_column("ID", justify="right")
    table.add_column("Task", style="bold")
    table.add_column("Type")
    table.add_column("Message", max_width=40)
    table.add_column("When")

    for e in errors:
        msg = (e.error_message or "")[:40]
        when = e.occurred_at[:19] if e.occurred_at else "-"
        color = ERROR_TYPE_COLORS.get(e.error_type, "")
        type_text = f"[{color}]{e.error_type}[/{color}]" if color else e.error_type
        table.add_row(str(e.id), e.task_name, type_text, msg, when)

    console.print(table)


def show_tickets(db: Database, status: str = None):
    tickets = db.get_tickets(status)
    if not tickets:
        console.print("[dim]No remediation tickets found.[/dim]")
        return

    table = Table(title="Remediation Tickets")
    table.add_column("ID", justify="right")
    table.add_column("Task", style="bold")
    table.add_column("Status")
    table.add_column("Created")

    for t in tickets:
        created = t.created_at[:19] if t.created_at else "-"
        color = TICKET_COLORS.get(t.status, "")
        status_text = f"[{color}]{t.status}[/{color}]" if color else t.status
        table.add_row(str(t.id), t.task_name, status_text, created)

    console.print(table)


def show_notifications(db: Database, unread_only: bool = True, limit: int = 30):
    where = " WHERE read=0" if unread_only else ""
    rows = db.execute(
        f"SELECT * FROM notifications{where}"
        f" ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    unread = db.execute(
        "SELECT COUNT(*) FROM notifications WHERE read=0").fetchone()[0]

    if not rows:
        label = "unread " if unread_only else ""
        console.print(f"[dim]No {label}notifications. All clear.[/dim]")
        return

    header = f"Inbox ({unread} unread)" if unread else "Inbox"
    console.rule(f"[bold]{header}[/bold]")
    console.print()

    for r in rows:
        icon = SEVERITY_ICONS.get(r["severity"], " ")
        severity = r["severity"] or "info"
        when = r["sent_at"][5:16].replace("T", " ") if r["sent_at"] else ""
        unread_mark = "[bold]*[/bold] " if not r["read"] else "  "
        task = r["task_name"] or ""
        border_color = SEVERITY_COLORS.get(severity, "white")

        title = f"{unread_mark}{icon} #{r['id']}  {severity.upper():<7} {task}"
        body = r["message"][:70]
        if r["action_cmd"]:
            body += f"\n[dim]-> {r['action_cmd']}[/dim]"

        panel = Panel(
            body,
            title=title,
            title_align="left",
            subtitle=f"[dim]{when}[/dim]",
            subtitle_align="right",
            border_style=border_color,
            expand=True,
            padding=(0, 1),
        )
        console.print(panel)

    if unread:
        console.print()
        console.print(f"  [dim]{unread} unread. Commands:[/dim]")
        console.print("    [dim]cs notifications --mark-read     Mark all as read[/dim]")
        console.print("    [dim]cs notifications --act <ID>      Execute action[/dim]")
        console.print("    [dim]cs notifications --all           Show all (inc. read)[/dim]")
    console.print()


def mark_notifications_read(db: Database):
    db.execute("UPDATE notifications SET read=1 WHERE read=0")
    db.conn.commit()
    console.print("[green]All notifications marked as read.[/green]")


def act_on_notification(db: Database, notification_id: int):
    import subprocess
    row = db.execute("SELECT * FROM notifications WHERE id=?",
                     (notification_id,)).fetchone()
    if not row:
        console.print(f"[red]Notification #{notification_id} not found.[/red]")
        return
    if not row["action_cmd"]:
        console.print(f"[red]Notification #{notification_id} has no action.[/red]")
        return
    db.execute("UPDATE notifications SET read=1 WHERE id=?",
               (notification_id,))
    db.conn.commit()
    console.print(f"[bold]Executing: {row['action_cmd']}[/bold]")
    subprocess.run(row["action_cmd"], shell=True)


def show_doctor(db: Database, tasks_dir: Path, logs_dir: Path):
    import shutil, subprocess

    console.rule("[bold]Claude Scheduler Health Check[/bold]")
    console.print()

    try:
        subprocess.run(["claude", "--version"], capture_output=True, timeout=5)
        console.print(f"[{DOCTOR_OK}] claude CLI found")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        console.print(f"[{DOCTOR_FAIL}] claude CLI not found in PATH")

    tasks = find_tasks(tasks_dir)
    enabled = [t for t in tasks if t.enabled]
    console.print(f"[{DOCTOR_OK}] {len(tasks)} task files, {len(enabled)} enabled")

    stale = db.recover_stale_runs()
    if stale:
        console.print(f"[{DOCTOR_FAIL}] Recovered {len(stale)} stale runs (marked as crashed)")
    else:
        console.print(f"[{DOCTOR_OK}] No stale runs")

    tickets = db.get_tickets(status="open")
    if tickets:
        console.print(f"[{DOCTOR_FAIL}] {len(tickets)} open remediation ticket(s)")
    else:
        console.print(f"[{DOCTOR_OK}] No open tickets")

    usage = shutil.disk_usage(logs_dir if logs_dir.exists() else "/")
    free_gb = usage.free / (1024**3)
    console.print(f"[{DOCTOR_OK}] {free_gb:.1f} GB free disk space")

    zshrc = Path.home() / ".zshrc"
    if zshrc.exists() and "register-python-argcomplete cs" in zshrc.read_text():
        console.print(f"[{DOCTOR_OK}] Shell completion configured")
    else:
        console.print(f"[{DOCTOR_FAIL}] Shell completion not configured")
        console.print('         Run: eval "$(register-python-argcomplete cs)"', style="dim")
