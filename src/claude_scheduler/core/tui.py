"""Terminal TUI dashboard using Textual."""
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import (
    Header, Footer, Static, DataTable, TabbedContent,
    TabPane, Label, Input, Button, RichLog,
)
from textual.binding import Binding
from textual.timer import Timer
from pathlib import Path
from datetime import datetime

from .db import Database
from .parser import find_tasks
from .models import Task


class StatusTable(DataTable):
    """Task status dashboard table."""

    def populate(self, db: Database, tasks_dir: Path):
        self.clear(columns=True)
        self.add_columns("Task", "Schedule", "Status", "Failures", "Runs", "Last Run")
        tasks = find_tasks(tasks_dir)
        states = {s["task_name"]: s for s in db.get_all_task_states()}
        for task in tasks:
            s = states.get(task.name, {})
            status = s.get("last_status", "never")
            consec = s.get("consecutive_failures", 0)
            total = s.get("total_runs", 0)
            last = s.get("last_run_at", "-")
            if last and last != "-":
                last = last[:19]
            style = {
                "success": "green", "failed": "red",
                "timeout": "yellow", "never": "dim",
            }.get(status, "white")
            alert = " [red]![/]" if consec >= 3 else ""
            self.add_row(
                task.name, task.schedule,
                f"[{style}]{status}[/]{alert}",
                str(consec), str(total), last,
            )


class HistoryTable(DataTable):
    """Run history table."""

    def populate(self, db: Database, task_filter: str = None):
        self.clear(columns=True)
        self.add_columns("ID", "Task", "Status", "Duration", "Attempt", "Started")
        runs = db.get_run_history(task_filter, limit=50)
        for r in runs:
            dur = f"{r.duration_seconds:.1f}s" if r.duration_seconds else "-"
            started = r.started_at[:19] if r.started_at else "-"
            style = {"success": "green", "failed": "red",
                     "timeout": "yellow", "crashed": "magenta"}.get(r.status, "white")
            self.add_row(
                str(r.id), r.task_name,
                f"[{style}]{r.status}[/]",
                dur, str(r.attempt), started,
            )


class ErrorsTable(DataTable):
    """Error records table."""

    def populate(self, db: Database, task_filter: str = None):
        self.clear(columns=True)
        self.add_columns("ID", "Task", "Type", "Message", "When")
        errors = db.get_errors(task_filter, limit=50)
        for e in errors:
            msg = (e.error_message or "")[:50]
            when = e.occurred_at[:19] if e.occurred_at else "-"
            self.add_row(str(e.id), e.task_name, e.error_type, msg, when)


class TicketsTable(DataTable):
    """Remediation tickets table."""

    def populate(self, db: Database, status_filter: str = None):
        self.clear(columns=True)
        self.add_columns("ID", "Task", "Status", "Created", "Investigation")
        tickets = db.get_tickets(status_filter)
        for t in tickets:
            created = t.created_at[:19] if t.created_at else "-"
            inv = (t.investigation or "")[:40]
            style = {"open": "red", "investigating": "yellow",
                     "resolved": "green", "closed": "dim"}.get(t.status, "white")
            self.add_row(
                str(t.id), t.task_name,
                f"[{style}]{t.status}[/]",
                created, inv,
            )


class NotificationsTable(DataTable):
    """Notification inbox table."""

    def populate(self, db: Database, unread_only: bool = True):
        self.clear(columns=True)
        self.add_columns("", "ID", "Severity", "Task", "Message", "When")
        where = " WHERE read=0" if unread_only else ""
        rows = db.execute(
            f"SELECT * FROM notifications{where}"
            f" ORDER BY id DESC LIMIT 50").fetchall()
        for r in rows:
            when = r["sent_at"][5:16].replace("T", " ") if r["sent_at"] else "-"
            msg = (r["message"] or "")[:50]
            unread = "[bold]*[/]" if not r["read"] else " "
            sev = r["severity"]
            style = {"error": "red", "action": "yellow",
                     "warning": "#ff8800", "info": "green"}.get(sev, "white")
            self.add_row(
                unread, str(r["id"]),
                f"[{style}]{sev.upper()}[/]",
                r["task_name"] or "-", msg, when,
            )


class SchedulerApp(App):
    """Claude Scheduler TUI Dashboard."""

    TITLE = "Claude Scheduler"
    CSS_PATH = "tui.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("d", "tab_dashboard", "Dashboard", show=False),
        Binding("h", "tab_history", "History", show=False),
        Binding("e", "tab_errors", "Errors", show=False),
        Binding("t", "tab_tickets", "Tickets", show=False),
    ]

    def __init__(self, db: Database, tasks_dir: Path, logs_dir: Path):
        super().__init__()
        self.db = db
        self.tasks_dir = tasks_dir
        self.logs_dir = logs_dir
        self._refresh_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="tabs"):
            with TabPane("Dashboard", id="tab-dashboard"):
                yield StatusTable(id="status-table")
            with TabPane("History", id="tab-history"):
                yield HistoryTable(id="history-table")
            with TabPane("Errors", id="tab-errors"):
                yield ErrorsTable(id="errors-table")
            with TabPane("Tickets", id="tab-tickets"):
                yield TicketsTable(id="tickets-table")
                yield Static(id="ticket-detail")
            with TabPane("Notifications", id="tab-notifications"):
                yield NotificationsTable(id="notifications-table")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_all()
        self._refresh_timer = self.set_interval(30, self.refresh_all)

    def refresh_all(self) -> None:
        self.query_one("#status-table", StatusTable).populate(
            self.db, self.tasks_dir)
        self.query_one("#history-table", HistoryTable).populate(self.db)
        self.query_one("#errors-table", ErrorsTable).populate(self.db)
        self.query_one("#tickets-table", TicketsTable).populate(self.db)
        self.query_one("#notifications-table", NotificationsTable).populate(self.db)

    def action_refresh(self) -> None:
        self.refresh_all()
        self.notify("Refreshed", severity="information", timeout=2)

    def action_tab_dashboard(self) -> None:
        self.query_one("#tabs", TabbedContent).active = "tab-dashboard"

    def action_tab_history(self) -> None:
        self.query_one("#tabs", TabbedContent).active = "tab-history"

    def action_tab_errors(self) -> None:
        self.query_one("#tabs", TabbedContent).active = "tab-errors"

    def action_tab_tickets(self) -> None:
        self.query_one("#tabs", TabbedContent).active = "tab-tickets"

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table = event.data_table
        if table.id == "tickets-table":
            row = event.cursor_row
            cells = table.get_row_at(row)
            if cells:
                ticket_id = int(cells[0])
                try:
                    ticket = self.db.get_ticket(ticket_id)
                    detail = self.query_one("#ticket-detail", Static)
                    detail.update(
                        f"[bold]Ticket #{ticket.id}[/] — {ticket.task_name}\n"
                        f"Status: {ticket.status}\n"
                        f"Created: {ticket.created_at}\n\n"
                        f"[bold]Investigation:[/]\n{ticket.investigation or '(none)'}\n\n"
                        f"[bold]Resolution:[/]\n{ticket.resolution or '(pending)'}\n\n"
                        f"[bold]User Guidance:[/]\n{ticket.user_guidance or '(none)'}\n\n"
                        f"[dim]Remediate: ./cs remediate {ticket.id} --guidance '...'[/]"
                    )
                except ValueError:
                    pass


def run_tui(db: Database, tasks_dir: Path, logs_dir: Path):
    app = SchedulerApp(db, tasks_dir, logs_dir)
    app.run()
