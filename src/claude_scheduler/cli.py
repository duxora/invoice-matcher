#!/usr/bin/env python3
"""cs — Claude Scheduler CLI."""
import argcomplete
import argparse
import sys
from pathlib import Path

from rich.table import Table
from rich.panel import Panel
from claude_scheduler import __version__
from claude_scheduler.console import console
from claude_scheduler.config import get_config, init_config


def get_db():
    from claude_scheduler.core.db import Database
    cfg = get_config()
    cfg.paths.data_dir.mkdir(parents=True, exist_ok=True)
    return Database(cfg.paths.data_dir / "scheduler.db")


# ── Init ──

def cmd_init(args):
    cfg = init_config()
    console.print("[green]Initialized claude-scheduler[/green]")
    console.print(f"  Config: {cfg.paths.tasks_dir.parent / 'config.toml'}")
    console.print(f"  Tasks:  {cfg.paths.tasks_dir}")
    console.print(f"  Logs:   {cfg.paths.logs_dir}")
    console.print(f"  Data:   {cfg.paths.data_dir}")
    console.print("\nNext: [bold]cs new[/bold] to create your first task")


# ── Serve ──

def cmd_serve(args):
    cfg = get_config()
    port = args.port or cfg.server.port
    host = cfg.server.host

    if args.install:
        from claude_scheduler.core.platform import install_service
        install_service(port, "cs")
        return
    if args.uninstall:
        from claude_scheduler.core.platform import uninstall_service
        uninstall_service()
        return

    import uvicorn
    from claude_scheduler.web.app import app
    console.print(f"Dashboard at [bold]http://{host}:{port}[/bold]")
    uvicorn.run(app, host=host, port=port, log_level="info")


# ── Task management ──

TASK_TEMPLATE = """\
# name: {name}
# schedule: {schedule}
# workdir: {workdir}
# model: claude-sonnet-4-6
# tools: Read,Grep,Glob
# max_turns: 10
# timeout: 300
# retry: 1
# notify: errors
# on_failure: investigate
# enabled: true
---
{prompt}
"""

def cmd_new(args):
    import os, subprocess
    cfg = get_config()
    tasks_dir = cfg.paths.tasks_dir
    tasks_dir.mkdir(parents=True, exist_ok=True)

    if args.edit:
        edit_path = Path(args.edit)
        if not edit_path.exists():
            console.print(f"[red]File not found: {edit_path}[/red]")
            return
        editor = os.environ.get("EDITOR", "vim")
        subprocess.call([editor, str(edit_path)])
        console.print(f"[green]Updated:[/green] {edit_path}")
        return

    name = args.name or input("Task name: ").strip()
    slug = name.lower().replace(" ", "-").strip("-")
    path = tasks_dir / f"{slug}.task"

    if args.prompt:
        schedule = args.schedule or "daily 09:00"
        workdir = args.workdir or str(Path.home() / "workspace")
        path.write_text(TASK_TEMPLATE.format(
            name=name, schedule=schedule,
            workdir=workdir, prompt=args.prompt + "\n",
        ))
        console.print(f"[green]Created:[/green] {path}")
        console.print(f"[bold]Edit:[/bold]    cs new --edit {path}")
        console.print(f"[bold]Test:[/bold]    cs run {path} --dry-run")
    else:
        schedule = args.schedule or input("Schedule (daily HH:MM / weekly DAY HH:MM / every Nh): ").strip()
        workdir = args.workdir or input(f"Working directory [{Path.home() / 'workspace'}]: ").strip()
        workdir = workdir or str(Path.home() / "workspace")

        template = TASK_TEMPLATE.format(
            name=name, schedule=schedule, workdir=workdir,
            prompt="# Write your prompt here.\n# Multi-line supported.\n",
        )
        path.write_text(template)

        editor = os.environ.get("EDITOR", "vim")
        console.print(f"\n[bold]Opening {editor} for prompt...[/bold]\n")
        subprocess.call([editor, str(path)])

        if not path.exists() or path.stat().st_size == 0:
            console.print("[red]Aborted — empty file.[/red]")
            return

        console.print(f"[green]Created:[/green] {path}")
        console.print(f"[bold]Test:[/bold]    cs run {path} --dry-run")


def _set_enabled(slug: str, enabled: bool):
    import re
    cfg = get_config()
    tasks_dir = cfg.paths.tasks_dir
    tasks_dir.mkdir(parents=True, exist_ok=True)
    for f in tasks_dir.glob("*.task"):
        text = f.read_text()
        if "# name:" in text:
            name_match = re.search(r'^# name:\s+(.+)$', text, re.MULTILINE)
            if name_match:
                name = name_match.group(1).strip()
                task_slug = name.lower().replace(" ", "-").strip("-")
                if task_slug == slug:
                    val = "true" if enabled else "false"
                    if re.search(r'^# enabled:', text, re.MULTILINE):
                        text = re.sub(r'^(# enabled:)\s+\w+', f'\\1 {val}', text,
                                      flags=re.MULTILINE)
                    else:
                        text = text.replace("\n---", f"\n# enabled: {val}\n---", 1)
                    f.write_text(text)
                    if enabled:
                        console.print(f"[green]Enabled[/green]: {name}")
                    else:
                        console.print(f"[red]Disabled[/red]: {name}")
                    return
    console.print(f"[red]Task with slug '{slug}' not found[/red]")

def cmd_enable(args):
    _set_enabled(args.task_slug, True)

def cmd_disable(args):
    _set_enabled(args.task_slug, False)


# ── Execution ──

def cmd_run(args):
    from claude_scheduler.core.parser import parse_task
    task = parse_task(Path(args.task_file))
    if args.dry_run:
        from claude_scheduler.core.executor import build_claude_command
        cmd = build_claude_command(task)
        t = Table(show_header=False, box=None)
        t.add_row("[bold]Task[/bold]", task.name)
        t.add_row("[bold]Schedule[/bold]", task.schedule)
        t.add_row("[bold]Workdir[/bold]", task.workdir or "(current)")
        t.add_row("[bold]Model[/bold]", task.model)
        t.add_row("[bold]Tools[/bold]", task.tools)
        t.add_row("[bold]Turns[/bold]", str(task.max_turns))
        t.add_row("[bold]Timeout[/bold]", f"{task.timeout}s")
        t.add_row("[bold]Retry[/bold]", f"{task.retry}x (delay: {task.retry_delay}s)")
        t.add_row("[bold]On fail[/bold]", task.on_failure)
        t.add_row("[bold]Command[/bold]", f"{' '.join(cmd[:6])}...")
        console.print(t)
        return
    db = get_db()
    cfg = get_config()
    from claude_scheduler.core.orchestrator import Orchestrator
    orch = Orchestrator(cfg.paths.tasks_dir, cfg.paths.logs_dir, db)
    orch.run_single(task)
    db.close()

def cmd_run_all(args):
    db = get_db()
    cfg = get_config()
    from claude_scheduler.core.orchestrator import Orchestrator
    orch = Orchestrator(cfg.paths.tasks_dir, cfg.paths.logs_dir, db)
    results = orch.run_schedule(args.schedule or "all")
    console.print(f"\nResults: [green]{results['success']}[/green]/{results['total']} succeeded, [red]{results['failed']}[/red] failed")
    db.close()


# ── Monitoring ──

def cmd_status(args):
    from claude_scheduler.core import monitor
    db = get_db()
    cfg = get_config()
    monitor.show_status(db, cfg.paths.tasks_dir)
    db.close()

def cmd_history(args):
    from claude_scheduler.core import monitor
    db = get_db()
    monitor.show_history(db, args.task, args.n)
    db.close()

def cmd_errors(args):
    from claude_scheduler.core import monitor
    db = get_db()
    monitor.show_errors(db, args.task)
    db.close()

def cmd_tickets(args):
    from claude_scheduler.core import monitor
    db = get_db()
    monitor.show_tickets(db, args.status)
    db.close()

def cmd_notifications(args):
    from claude_scheduler.core import monitor
    db = get_db()
    if args.mark_read:
        monitor.mark_notifications_read(db)
    elif args.act is not None:
        monitor.act_on_notification(db, args.act)
    else:
        monitor.show_notifications(db, unread_only=not args.all)
    db.close()

def cmd_doctor(args):
    from claude_scheduler.core import monitor
    db = get_db()
    cfg = get_config()
    monitor.show_doctor(db, cfg.paths.tasks_dir, cfg.paths.logs_dir)
    db.close()

def cmd_dashboard(args):
    db = get_db()
    cfg = get_config()
    from claude_scheduler.core.tui import run_tui
    run_tui(db, cfg.paths.tasks_dir, cfg.paths.logs_dir)
    db.close()

def cmd_logs(args):
    import subprocess
    cfg = get_config()
    files = sorted(cfg.paths.logs_dir.glob(f"*{args.task}*"), key=lambda f: f.stat().st_mtime)
    if not files:
        console.print(f"[dim]No logs found for '{args.task}'[/dim]")
        return
    latest = files[-1]
    if args.follow:
        subprocess.run(["tail", "-f", str(latest)])
    else:
        print(latest.read_text())


# ── Remediation & Approvals ──

def cmd_remediate(args):
    db = get_db()
    cfg = get_config()
    from claude_scheduler.core.orchestrator import Orchestrator
    orch = Orchestrator(cfg.paths.tasks_dir, cfg.paths.logs_dir, db)
    orch.remediate_ticket(args.ticket_id, args.guidance or "")
    db.close()

def cmd_approvals(args):
    db = get_db()
    approvals = db.get_pending_approvals()
    if not approvals:
        console.print("[dim]No pending approvals.[/dim]")
        db.close()
        return
    t = Table(title="Pending Approvals")
    t.add_column("ID", style="bold")
    t.add_column("Task")
    t.add_column("Artifact")
    t.add_column("Created")
    for a in approvals:
        created = a["created_at"][:19] if a["created_at"] else "-"
        t.add_row(str(a["id"]), a["task_name"], f"#{a['artifact_id']}", created)
    console.print(t)
    db.close()

def cmd_approve(args):
    db = get_db()
    db.update_approval(args.approval_id, "approved", args.note or "")
    console.print(f"[green]Approval #{args.approval_id} approved.[/green]")
    db.close()

def cmd_reject(args):
    db = get_db()
    db.update_approval(args.rejection_id, "rejected", args.note or "")
    console.print(f"[red]Approval #{args.rejection_id} rejected.[/red]")
    db.close()

def cmd_artifacts(args):
    db = get_db()
    artifacts = db.get_artifacts(args.task_name)
    if not artifacts:
        console.print(f"[dim]No artifacts for '{args.task_name}'.[/dim]")
        db.close()
        return
    for a in artifacts:
        console.print(Panel(
            a["content"][:2000],
            title=f"Artifact #{a['id']} ({a['artifact_type']}) -- {a['created_at'][:19]}"))
    db.close()


# ── Course feedback ──

def cmd_feedback(args):
    """Record feedback for a course lesson."""
    import json
    course_dir = Path.home() / ".config" / "claude-scheduler" / "courses" / args.course
    progress_file = course_dir / "progress.json"
    if not progress_file.exists():
        console.print(f"[red]Course '{args.course}' not found[/red]")
        return
    data = json.loads(progress_file.read_text())
    entry = {
        "day": data["current_day"] - 1,
        "rating": args.rating,
        "note": args.note or "",
    }
    data.setdefault("feedback", []).append(entry)
    progress_file.write_text(json.dumps(data, indent=2))
    console.print(f"[green]Feedback recorded[/green] for day {entry['day']}: rating {args.rating}/5")


# ── Workflow ──

def cmd_workflow_run(args):
    from claude_scheduler.workflow.parser import parse_workflow
    from claude_scheduler.workflow.runner import WorkflowRunner
    cfg = get_config()
    wf = parse_workflow(Path(args.workflow_file))
    if args.dry_run:
        t = Table(show_header=False, box=None)
        t.add_row("[bold]Workflow[/bold]", wf.name)
        t.add_row("[bold]Trigger[/bold]", wf.trigger)
        t.add_row("[bold]Steps[/bold]", str(len(wf.steps)))
        t.add_row("[bold]Security[/bold]", wf.security_level)
        for s in wf.steps:
            t.add_row(f"  Step {s.order}", s.description)
        console.print(t)
        return
    runner = WorkflowRunner(logs_dir=cfg.paths.logs_dir)
    result = runner.run(wf)
    if result["status"] == "success":
        console.print(f"[green]Workflow '{wf.name}' completed successfully[/green]")
    else:
        console.print(f"[red]Workflow '{wf.name}' failed at step {result.get('failed_step')}[/red]")

def cmd_workflow_list(args):
    from claude_scheduler.workflow.parser import find_workflows
    cfg = get_config()
    workflows = find_workflows(cfg.paths.tasks_dir)
    if not workflows:
        console.print("[dim]No workflows found.[/dim]")
        return
    t = Table(title="Workflows")
    t.add_column("Name")
    t.add_column("Trigger")
    t.add_column("Steps")
    t.add_column("Security")
    for wf in workflows:
        t.add_row(wf.name, wf.trigger, str(len(wf.steps)), wf.security_level)
    console.print(t)

def cmd_workflow_from_sop(args):
    console.print("[yellow]SOP converter will be implemented in Phase 5[/yellow]")


# ── Gateway ──

def cmd_gateway_audit(args):
    from claude_scheduler.gateway.audit import AuditLogger
    cfg = get_config()
    logger = AuditLogger(cfg.paths.data_dir / "audit.jsonl")
    entries = logger.query(task=args.task or "")
    if not entries:
        console.print("[dim]No audit entries found.[/dim]")
        return
    t = Table(title="Audit Log")
    t.add_column("Time")
    t.add_column("Task")
    t.add_column("Tool")
    t.add_column("Args", max_width=40)
    t.add_column("Decision")
    t.add_column("Reason")
    for e in entries[-50:]:
        style = "green" if e["decision"] == "allow" else "red"
        t.add_row(
            e["ts"][:19], e["task"], e["tool"],
            e.get("args", "")[:40], f"[{style}]{e['decision']}[/{style}]",
            e.get("reason", ""),
        )
    console.print(t)

def cmd_gateway_policy_list(args):
    from claude_scheduler.gateway.policy import load_policies
    cfg = get_config()
    policy_file = cfg.paths.tasks_dir.parent / "policies" / "default.toml"
    if not policy_file.exists():
        console.print(f"[dim]No policy file at {policy_file}[/dim]")
        return
    policies = load_policies(policy_file)
    for name, p in policies.items():
        console.print(Panel(
            f"Tools: {', '.join(p.allowed_tools)}\n"
            f"Denied: {', '.join(p.denied_patterns)}\n"
            f"Bash: {', '.join(p.bash_allowlist) or 'any'}\n"
            f"Approval: {', '.join(p.require_approval) or 'none'}\n"
            f"Rate: {p.max_calls_per_minute}/min\n"
            f"Network isolation: {p.network_isolation}",
            title=f"Policy: {name}",
        ))


# ── Argument parser ──

def main():
    parser = argparse.ArgumentParser(
        prog="cs",
        description="Claude Scheduler — scheduled AI tasks for Claude Code",
    )
    parser.add_argument("--version", "-V", action="version", version=f"claude-scheduler {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    # init
    p = sub.add_parser("init", help="First-time setup")
    p.set_defaults(func=cmd_init)

    # serve
    p = sub.add_parser("serve", help="Start web dashboard")
    p.add_argument("--port", "-p", type=int, default=None, help="Port (default: from config)")
    p.add_argument("--install", action="store_true", help="Install as system service (auto-start on login)")
    p.add_argument("--uninstall", action="store_true", help="Remove system service")
    p.set_defaults(func=cmd_serve)

    # new
    p = sub.add_parser("new", help="Create a new task")
    p.add_argument("--name", help="Task name")
    p.add_argument("--schedule", help="Schedule (e.g. 'daily 09:00', 'every 2h')")
    p.add_argument("--workdir", help="Working directory")
    p.add_argument("--prompt", help="Inline prompt (skips editor)")
    p.add_argument("--edit", metavar="FILE", help="Open existing .task file in $EDITOR")
    p.set_defaults(func=cmd_new)

    # enable / disable
    p = sub.add_parser("enable", help="Enable a task")
    p.add_argument("task_slug")
    p.set_defaults(func=cmd_enable)

    p = sub.add_parser("disable", help="Disable a task")
    p.add_argument("task_slug")
    p.set_defaults(func=cmd_disable)

    # run
    p = sub.add_parser("run", help="Run a single task")
    p.add_argument("task_file")
    p.add_argument("--dry-run", action="store_true", help="Preview without executing")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("run-all", help="Run all enabled tasks")
    p.add_argument("--schedule", "-s", default="all")
    p.set_defaults(func=cmd_run_all)

    # monitoring
    p = sub.add_parser("status", help="Task status dashboard")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("history", help="Run history")
    p.add_argument("--task", "-t")
    p.add_argument("-n", type=int, default=20)
    p.set_defaults(func=cmd_history)

    p = sub.add_parser("errors", help="Error log")
    p.add_argument("--task", "-t")
    p.set_defaults(func=cmd_errors)

    p = sub.add_parser("tickets", help="Remediation tickets")
    p.add_argument("--status", "-s")
    p.set_defaults(func=cmd_tickets)

    p = sub.add_parser("notifications", help="Notification inbox")
    p.add_argument("--all", "-a", action="store_true", help="Show all (inc. read)")
    p.add_argument("--mark-read", action="store_true")
    p.add_argument("--act", type=int, metavar="ID")
    p.set_defaults(func=cmd_notifications)

    p = sub.add_parser("doctor", help="Health check")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("dashboard", help="TUI dashboard")
    p.set_defaults(func=cmd_dashboard)

    p = sub.add_parser("logs", help="View task logs")
    p.add_argument("task")
    p.add_argument("--follow", "-f", action="store_true")
    p.set_defaults(func=cmd_logs)

    # remediation & approvals
    p = sub.add_parser("remediate", help="Trigger ticket remediation")
    p.add_argument("ticket_id", type=int)
    p.add_argument("--guidance", "-g")
    p.set_defaults(func=cmd_remediate)

    p = sub.add_parser("approvals", help="List pending approvals")
    p.set_defaults(func=cmd_approvals)

    p = sub.add_parser("approve", help="Approve a pending item")
    p.add_argument("approval_id", type=int)
    p.add_argument("--note", "-n")
    p.set_defaults(func=cmd_approve)

    p = sub.add_parser("reject", help="Reject a pending item")
    p.add_argument("rejection_id", type=int)
    p.add_argument("--note", "-n")
    p.set_defaults(func=cmd_reject)

    p = sub.add_parser("artifacts", help="Show task artifacts")
    p.add_argument("task_name")
    p.set_defaults(func=cmd_artifacts)

    # course feedback
    p = sub.add_parser("feedback", help="Rate a course lesson")
    p.add_argument("course", help="Course name (e.g. pm-ai-era)")
    p.add_argument("--rating", "-r", type=int, required=True, choices=[1, 2, 3, 4, 5])
    p.add_argument("--note", "-n", help="Optional feedback note")
    p.set_defaults(func=cmd_feedback)

    # workflow
    wf_parser = sub.add_parser("workflow", help="Workflow management")
    wf_sub = wf_parser.add_subparsers(dest="wf_command", required=True)

    p = wf_sub.add_parser("run", help="Run a workflow")
    p.add_argument("workflow_file")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_workflow_run)

    p = wf_sub.add_parser("list", help="List workflows")
    p.set_defaults(func=cmd_workflow_list)

    p = wf_sub.add_parser("from-sop", help="Convert SOP to workflow")
    p.add_argument("sop_file")
    p.set_defaults(func=cmd_workflow_from_sop)

    # gateway
    gw_parser = sub.add_parser("gateway", help="Security gateway")
    gw_sub = gw_parser.add_subparsers(dest="gw_command", required=True)

    p = gw_sub.add_parser("audit", help="View audit log")
    p.add_argument("--task", "-t")
    p.set_defaults(func=cmd_gateway_audit)

    p = gw_sub.add_parser("policy", help="List policies")
    p.set_defaults(func=cmd_gateway_policy_list)

    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
