"""Scheduler web routes — dashboard, history, errors, tickets, and task management."""
import shutil
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from server.config import SCHEDULER_DIR, TASKS_DIR, LOGS_DIR, DATA_DIR

# Make scheduler package importable
sys.path.insert(0, str(SCHEDULER_DIR))
from scheduler.db import Database
from scheduler.parser import find_tasks, parse_task

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_db() -> Database:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return Database(DATA_DIR / "scheduler.db")


def app_context(request: Request, **kwargs):
    """Build template context with sidebar navigation data."""
    from server.main import APPS
    return {"request": request, "apps": APPS, **kwargs}


def _slug(name: str) -> str:
    return name.lower().replace(" ", "-").strip("-")


def _find_task_by_slug(slug: str):
    """Return (Task, error_string) — one of them is always None."""
    tasks = find_tasks(TASKS_DIR)
    for t in tasks:
        if t.slug == slug:
            return t, None
    return None, f"Task '{slug}' not found"


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    db = get_db()
    try:
        tasks = find_tasks(TASKS_DIR)
        states = db.get_all_task_states()
        states_map = {s["task_name"]: s for s in states}
        runs = db.get_run_history(limit=100)
        total_cost = sum(r.cost_usd for r in runs)
        stats = {
            "total_tasks": len(tasks),
            "enabled": sum(1 for t in tasks if t.enabled),
            "disabled": sum(1 for t in tasks if not t.enabled),
            "total_runs": len(runs),
            "successes": sum(1 for r in runs if r.status == "success"),
            "failures": sum(1 for r in runs if r.status in ("failed", "timeout")),
            "total_cost": total_cost,
        }
        return templates.TemplateResponse("dashboard.html", app_context(
            request, tasks=tasks, states=states_map, stats=stats,
        ))
    finally:
        db.close()


@router.get("/partials/status-table", response_class=HTMLResponse)
async def status_table_partial(request: Request):
    """HTMX partial — returns just the task status table rows for live refresh."""
    db = get_db()
    try:
        tasks = find_tasks(TASKS_DIR)
        states = db.get_all_task_states()
        states_map = {s["task_name"]: s for s in states}
        return templates.TemplateResponse("partials/status_table.html", app_context(
            request, tasks=tasks, states=states_map,
        ))
    finally:
        db.close()


@router.get("/history", response_class=HTMLResponse)
async def history(
    request: Request,
    task: str = Query(default=None),
    n: int = Query(default=50),
):
    db = get_db()
    try:
        runs = db.get_run_history(task_name=task, limit=n)
        return templates.TemplateResponse("history.html", app_context(
            request, runs=runs, filter_task=task, limit=n,
        ))
    finally:
        db.close()


@router.get("/errors", response_class=HTMLResponse)
async def errors(
    request: Request,
    task: str = Query(default=None),
):
    db = get_db()
    try:
        errs = db.get_errors(task_name=task)
        return templates.TemplateResponse("errors.html", app_context(
            request, errors=errs, filter_task=task,
        ))
    finally:
        db.close()


@router.get("/tickets", response_class=HTMLResponse)
async def tickets(
    request: Request,
    status: str = Query(default=None),
):
    db = get_db()
    try:
        items = db.get_tickets(status=status)
        return templates.TemplateResponse("tickets.html", app_context(
            request, tickets=items, filter_status=status,
        ))
    finally:
        db.close()


@router.get("/notifications", response_class=HTMLResponse)
async def notifications(
    request: Request,
    all: str = Query(default=None),
):
    db = get_db()
    try:
        show_all = all == "true"
        items = db.get_notifications(unread_only=not show_all)
        return templates.TemplateResponse("notifications.html", app_context(
            request, notifications=items, show_all=show_all,
        ))
    finally:
        db.close()


@router.get("/doctor", response_class=HTMLResponse)
async def doctor(request: Request):
    checks = []

    # 1. Claude CLI available
    try:
        result = subprocess.run(
            ["claude", "--version"], capture_output=True, text=True, timeout=5,
        )
        checks.append({
            "name": "Claude CLI",
            "ok": result.returncode == 0,
            "detail": result.stdout.strip() if result.returncode == 0 else result.stderr.strip(),
        })
    except Exception as e:
        checks.append({"name": "Claude CLI", "ok": False, "detail": str(e)})

    # 2. Task count
    tasks = find_tasks(TASKS_DIR)
    checks.append({
        "name": "Task files",
        "ok": len(tasks) > 0,
        "detail": f"{len(tasks)} task(s) found in {TASKS_DIR}",
    })

    # 3. Stale runs
    db = get_db()
    try:
        stale = db.recover_stale_runs(max_age_seconds=3600)
        checks.append({
            "name": "Stale runs",
            "ok": len(stale) == 0,
            "detail": f"{len(stale)} stale run(s) recovered" if stale else "No stale runs",
        })

        # 4. Open tickets
        open_tickets = db.get_tickets(status="open")
        checks.append({
            "name": "Open tickets",
            "ok": len(open_tickets) == 0,
            "detail": f"{len(open_tickets)} open ticket(s)" if open_tickets else "No open tickets",
        })
    finally:
        db.close()

    # 5. Disk space
    usage = shutil.disk_usage("/")
    free_gb = usage.free / (1024 ** 3)
    checks.append({
        "name": "Disk space",
        "ok": free_gb > 1.0,
        "detail": f"{free_gb:.1f} GB free",
    })

    return templates.TemplateResponse("doctor.html", app_context(
        request, checks=checks,
    ))


@router.get("/tasks/{slug}", response_class=HTMLResponse)
async def task_detail(request: Request, slug: str):
    task, err = _find_task_by_slug(slug)
    if err:
        return HTMLResponse(f"<h1>404</h1><p>{err}</p>", status_code=404)

    db = get_db()
    try:
        runs = db.get_run_history(task_name=task.name, limit=20)
        errs = db.get_errors(task_name=task.name, limit=10)
        state = db.get_task_state(task.name)
        return templates.TemplateResponse("task_detail.html", app_context(
            request, task=task, runs=runs, errors=errs, state=state,
        ))
    finally:
        db.close()


@router.get("/tasks-new", response_class=HTMLResponse)
async def tasks_new_form(request: Request):
    return templates.TemplateResponse("task_new.html", app_context(request))


@router.get("/logs/{slug}", response_class=HTMLResponse)
async def view_log(request: Request, slug: str):
    task, err = _find_task_by_slug(slug)
    if err:
        return HTMLResponse(f"<h1>404</h1><p>{err}</p>", status_code=404)

    # Find most recent log file matching the task slug
    log_content = ""
    log_file = None
    if LOGS_DIR.exists():
        candidates = sorted(LOGS_DIR.glob(f"{slug}*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if candidates:
            log_file = candidates[0]
            raw = log_file.read_text(errors="replace")
            # Show last 5000 chars
            log_content = raw[-5000:] if len(raw) > 5000 else raw

    return templates.TemplateResponse("log_view.html", app_context(
        request, task=task, log_content=log_content,
        log_file=str(log_file) if log_file else None,
    ))


@router.get("/approvals", response_class=HTMLResponse)
async def approvals(request: Request):
    db = get_db()
    try:
        pending = db.get_pending_approvals()
        # Enrich with artifact content
        for item in pending:
            artifact = db.get_artifact(item["artifact_id"])
            item["artifact"] = artifact
        return templates.TemplateResponse("approvals.html", app_context(
            request, approvals=pending,
        ))
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Actions (POST — redirect via 303)
# ---------------------------------------------------------------------------

@router.post("/api/run/{slug}", response_class=HTMLResponse)
async def run_task(slug: str):
    task, err = _find_task_by_slug(slug)
    if err:
        return HTMLResponse(
            f'<span class="text-red-400">Task not found</span>',
            status_code=404,
        )

    db = get_db()
    try:
        from scheduler.orchestrator import Orchestrator
        orch = Orchestrator(tasks_dir=TASKS_DIR, logs_dir=LOGS_DIR, db=db)
        orch.run_single(task)
        state = db.get_task_state(task.name)
        status = state["last_status"] if state else "unknown"
        color = "green" if status == "success" else "red"
        return HTMLResponse(
            f'<span class="text-{color}-400 font-medium">{status}</span>'
        )
    except Exception as e:
        return HTMLResponse(
            f'<span class="text-red-400">Error: {e}</span>',
            status_code=500,
        )
    finally:
        db.close()


@router.post("/api/toggle/{slug}")
async def toggle_task(slug: str):
    task, err = _find_task_by_slug(slug)
    if err:
        return RedirectResponse(url="/scheduler/", status_code=303)

    # Toggle enabled flag in .task file
    content = task.file_path.read_text()
    if task.enabled:
        content = content.replace("# enabled: true", "# enabled: false", 1)
        if "# enabled:" not in content:
            # Insert enabled: false after the schedule line
            content = content.replace(
                f"# schedule: {task.schedule}",
                f"# schedule: {task.schedule}\n# enabled: false",
                1,
            )
    else:
        content = content.replace("# enabled: false", "# enabled: true", 1)

    task.file_path.write_text(content)
    return RedirectResponse(url="/scheduler/", status_code=303)


@router.post("/api/tickets/{ticket_id}/approve")
async def resolve_ticket(ticket_id: int):
    db = get_db()
    try:
        db.update_ticket(ticket_id, status="resolved")
    finally:
        db.close()
    return RedirectResponse(url="/scheduler/tickets", status_code=303)


@router.post("/api/notifications/mark-read")
async def mark_notifications_read():
    db = get_db()
    try:
        db.mark_notifications_read()
    finally:
        db.close()
    return RedirectResponse(url="/scheduler/notifications", status_code=303)


@router.post("/tasks-new")
async def create_task(
    request: Request,
    name: str = Form(...),
    schedule: str = Form(...),
    prompt: str = Form(...),
    model: str = Form(default="claude-sonnet-4-6"),
    max_turns: int = Form(default=10),
    timeout: int = Form(default=300),
    tools: str = Form(default="Read,Grep,Glob"),
    workdir: str = Form(default=""),
    enabled: bool = Form(default=True),
):
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    slug = _slug(name)
    task_path = TASKS_DIR / f"{slug}.task"

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

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(prompt.strip())
    lines.append("")

    task_path.write_text("\n".join(lines))
    return RedirectResponse(url=f"/scheduler/tasks/{slug}", status_code=303)


@router.post("/api/approvals/{approval_id}/approve")
async def approve(approval_id: int):
    db = get_db()
    try:
        db.update_approval(approval_id, status="approved")
    finally:
        db.close()
    return RedirectResponse(url="/scheduler/approvals", status_code=303)


@router.post("/api/approvals/{approval_id}/reject")
async def reject(approval_id: int):
    db = get_db()
    try:
        db.update_approval(approval_id, status="rejected")
    finally:
        db.close()
    return RedirectResponse(url="/scheduler/approvals", status_code=303)
