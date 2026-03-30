"""Tools Hub MCP Server — exposes scheduler tools to Claude Code."""
import shutil
import subprocess
from typing import Optional

from mcp.server.fastmcp import FastMCP

from claude_scheduler.config import get_config
from claude_scheduler.core.db import Database
from claude_scheduler.core.parser import find_tasks

mcp = FastMCP("tools-hub", instructions="Manage scheduled Claude tasks, view history, errors, tickets, and notifications.")


def _get_db() -> Database:
    cfg = get_config()
    cfg.paths.data_dir.mkdir(parents=True, exist_ok=True)
    return Database(cfg.paths.data_dir / "scheduler.db")


def _find_task_by_slug(slug: str):
    tasks = find_tasks(get_config().paths.tasks_dir)
    for t in tasks:
        if t.slug == slug:
            return t, None
    return None, f"Task '{slug}' not found"


# ---------------------------------------------------------------------------
# Read tools
# ---------------------------------------------------------------------------

@mcp.tool()
def scheduler_list_tasks() -> str:
    """List all scheduled tasks with their status, schedule, and last run info."""
    db = _get_db()
    try:
        tasks = find_tasks(get_config().paths.tasks_dir)
        states = {s["task_name"]: s for s in db.get_all_task_states()}
        lines = []
        for t in tasks:
            st = states.get(t.name, {})
            status = st.get("last_status", "never_run")
            last_run = st.get("last_run_at", "-")
            failures = st.get("consecutive_failures", 0)
            enabled = "enabled" if t.enabled else "DISABLED"
            lines.append(
                f"- **{t.name}** [{t.slug}] ({enabled})\n"
                f"  Schedule: {t.schedule} | Model: {t.model}\n"
                f"  Last: {status} @ {last_run} | Consecutive failures: {failures}"
            )
        if not lines:
            return "No tasks found."
        return f"**{len(tasks)} task(s):**\n\n" + "\n\n".join(lines)
    finally:
        db.close()


@mcp.tool()
def scheduler_task_detail(slug: str) -> str:
    """Get detailed info for a task including config, recent runs, and errors."""
    task, err = _find_task_by_slug(slug)
    if err:
        return err

    db = _get_db()
    try:
        runs = db.get_run_history(task_name=task.name, limit=10)
        errs = db.get_errors(task_name=task.name, limit=5)
        state = db.get_task_state(task.name)

        lines = [
            f"# {task.name}",
            f"- Slug: {task.slug}",
            f"- Schedule: {task.schedule}",
            f"- Model: {task.model}",
            f"- Enabled: {task.enabled}",
            f"- Timeout: {task.timeout}s | Max turns: {task.max_turns}",
            f"- Tools: {task.tools}",
            f"- Workdir: {task.workdir or '(default)'}",
            f"- File: {task.file_path}",
        ]

        if state:
            lines.append(f"\n## State")
            lines.append(f"- Last run: {state.get('last_status', '-')} @ {state.get('last_run_at', '-')}")
            lines.append(f"- Total runs: {state.get('total_runs', 0)} | Failures: {state.get('total_failures', 0)}")

        if runs:
            lines.append(f"\n## Recent Runs ({len(runs)})")
            for r in runs:
                cost = f"${r.cost_usd:.4f}" if r.cost_usd else "-"
                lines.append(f"- [{r.status}] {r.started_at} ({r.duration_seconds:.0f}s) cost={cost}")

        if errs:
            lines.append(f"\n## Recent Errors ({len(errs)})")
            for e in errs:
                lines.append(f"- [{e.error_type}] {e.occurred_at}: {e.error_message[:200]}")

        lines.append(f"\n## Prompt\n```\n{task.prompt}\n```")
        return "\n".join(lines)
    finally:
        db.close()


@mcp.tool()
def scheduler_history(task: Optional[str] = None, limit: int = 20) -> str:
    """View run history. Optionally filter by task name."""
    db = _get_db()
    try:
        runs = db.get_run_history(task_name=task, limit=limit)
        if not runs:
            return "No runs found."
        lines = [f"**Run history** ({len(runs)} runs):"]
        for r in runs:
            cost = f"${r.cost_usd:.4f}" if r.cost_usd else "-"
            err = f" | error: {r.error_message[:100]}" if r.error_message else ""
            lines.append(
                f"- **{r.task_name}** [{r.status}] {r.started_at} "
                f"({r.duration_seconds:.0f}s) cost={cost}{err}"
            )
        return "\n".join(lines)
    finally:
        db.close()


@mcp.tool()
def scheduler_errors(task: Optional[str] = None) -> str:
    """View error log. Optionally filter by task name."""
    db = _get_db()
    try:
        errs = db.get_errors(task_name=task)
        if not errs:
            return "No errors found."
        lines = [f"**{len(errs)} error(s):**"]
        for e in errs:
            lines.append(
                f"- **{e.task_name}** [{e.error_type}] {e.occurred_at}\n"
                f"  {e.error_message[:300]}"
            )
        return "\n".join(lines)
    finally:
        db.close()


@mcp.tool()
def scheduler_notifications(show_all: bool = False) -> str:
    """View notifications. By default shows unread only."""
    db = _get_db()
    try:
        items = db.get_notifications(unread_only=not show_all)
        if not items:
            return "No notifications." if not show_all else "No notifications found."
        lines = [f"**{len(items)} notification(s):**"]
        for n in items:
            read = "" if n.get("read") else " [UNREAD]"
            lines.append(
                f"- [{n['severity']}]{read} **{n['title']}** ({n.get('task_name', '-')})\n"
                f"  {n['message'][:200]}"
            )
        return "\n".join(lines)
    finally:
        db.close()


@mcp.tool()
def scheduler_tickets(status: Optional[str] = None) -> str:
    """View remediation tickets. Optionally filter by status (open/investigating/resolved/closed)."""
    db = _get_db()
    try:
        items = db.get_tickets(status=status)
        if not items:
            return "No tickets found."
        lines = [f"**{len(items)} ticket(s):**"]
        for t in items:
            lines.append(
                f"- #{t.id} **{t.task_name}** [{t.status}] {t.created_at}\n"
                f"  {t.investigation[:200] if t.investigation else '(no investigation)'}"
            )
        return "\n".join(lines)
    finally:
        db.close()


@mcp.tool()
def scheduler_doctor() -> str:
    """Run health checks on the scheduler system."""
    checks = []

    # Claude CLI
    try:
        result = subprocess.run(
            ["claude", "--version"], capture_output=True, text=True, timeout=5,
        )
        checks.append(("Claude CLI", result.returncode == 0,
                       result.stdout.strip() if result.returncode == 0 else result.stderr.strip()))
    except Exception as e:
        checks.append(("Claude CLI", False, str(e)))

    # Tasks
    tasks = find_tasks(get_config().paths.tasks_dir)
    checks.append(("Task files", len(tasks) > 0,
                   f"{len(tasks)} task(s) in {get_config().paths.tasks_dir}"))

    # Stale runs
    db = _get_db()
    try:
        stale = db.recover_stale_runs(max_age_seconds=3600)
        checks.append(("Stale runs", len(stale) == 0,
                       f"{len(stale)} recovered" if stale else "None"))

        open_tickets = db.get_tickets(status="open")
        checks.append(("Open tickets", len(open_tickets) == 0,
                       f"{len(open_tickets)} open" if open_tickets else "None"))
    finally:
        db.close()

    # Disk
    usage = shutil.disk_usage("/")
    free_gb = usage.free / (1024 ** 3)
    checks.append(("Disk space", free_gb > 1.0, f"{free_gb:.1f} GB free"))

    lines = ["**Health Check:**"]
    for name, ok, detail in checks:
        icon = "PASS" if ok else "FAIL"
        lines.append(f"- [{icon}] **{name}**: {detail}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Write tools
# ---------------------------------------------------------------------------

@mcp.tool()
def scheduler_run_task(slug: str) -> str:
    """Trigger an immediate run of a task by its slug."""
    task, err = _find_task_by_slug(slug)
    if err:
        return err

    db = _get_db()
    try:
        from claude_scheduler.core.orchestrator import Orchestrator
        cfg = get_config()
        orch = Orchestrator(tasks_dir=cfg.paths.tasks_dir, logs_dir=cfg.paths.logs_dir, db=db)
        orch.run_single(task)
        state = db.get_task_state(task.name)
        status = state["last_status"] if state else "unknown"
        return f"Task '{task.name}' completed with status: {status}"
    except Exception as e:
        return f"Error running task: {e}"
    finally:
        db.close()


@mcp.tool()
def scheduler_toggle_task(slug: str) -> str:
    """Enable or disable a task by its slug."""
    task, err = _find_task_by_slug(slug)
    if err:
        return err

    content = task.file_path.read_text()
    if task.enabled:
        content = content.replace("# enabled: true", "# enabled: false", 1)
        if "# enabled:" not in content:
            content = content.replace(
                f"# schedule: {task.schedule}",
                f"# schedule: {task.schedule}\n# enabled: false",
                1,
            )
        new_state = "disabled"
    else:
        content = content.replace("# enabled: false", "# enabled: true", 1)
        new_state = "enabled"

    task.file_path.write_text(content)
    return f"Task '{task.name}' is now {new_state}."


@mcp.tool()
def scheduler_create_task(
    name: str,
    schedule: str,
    prompt: str,
    model: str = "claude-sonnet-4-6",
    max_turns: int = 10,
    timeout: int = 300,
    tools: str = "Read,Grep,Glob",
    workdir: str = "",
    enabled: bool = True,
) -> str:
    """Create a new scheduled task.

    Args:
        name: Human-readable task name
        schedule: Cron expression (e.g. '0 9 * * *' for daily at 9am)
        prompt: The prompt Claude will execute
        model: Claude model to use
        max_turns: Maximum agentic turns
        timeout: Timeout in seconds
        tools: Comma-separated list of allowed tools
        workdir: Working directory for the task
        enabled: Whether the task starts enabled
    """
    tasks_dir = get_config().paths.tasks_dir
    tasks_dir.mkdir(parents=True, exist_ok=True)
    slug = name.lower().replace(" ", "-").strip("-")
    task_path = tasks_dir / f"{slug}.task"

    if task_path.exists():
        return f"Task file already exists: {task_path}"

    lines = [
        f"# name: {name}",
        f"# schedule: {schedule}",
        f"# model: {model}",
        f"# max_turns: {max_turns}",
        f"# timeout: {timeout}",
        f"# tools: {tools}",
    ]
    if workdir:
        lines.append(f"# workdir: {workdir}")
    if not enabled:
        lines.append("# enabled: false")

    lines.extend(["", "---", "", prompt.strip(), ""])
    task_path.write_text("\n".join(lines))
    return f"Created task '{name}' at {task_path}"


@mcp.tool()
def scheduler_resolve_ticket(ticket_id: int, resolution: str = "") -> str:
    """Resolve a remediation ticket by ID."""
    db = _get_db()
    try:
        db.update_ticket(ticket_id, status="resolved", resolution=resolution)
        return f"Ticket #{ticket_id} resolved."
    except ValueError as e:
        return str(e)
    finally:
        db.close()


@mcp.tool()
def scheduler_mark_notifications_read() -> str:
    """Mark all unread notifications as read."""
    db = _get_db()
    try:
        db.mark_notifications_read()
        return "All notifications marked as read."
    finally:
        db.close()


def main():
    mcp.run()


if __name__ == "__main__":
    main()
