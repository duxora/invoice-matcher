"""SQLite state store for task runs, errors, and remediation tickets."""
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from .models import RunRecord, ErrorRecord, Ticket

SCHEMA = """
CREATE TABLE IF NOT EXISTS task_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_name TEXT NOT NULL,
    task_file TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    exit_code INTEGER,
    attempt INTEGER DEFAULT 1,
    duration_seconds REAL,
    log_file TEXT,
    error_message TEXT,
    session_id TEXT
);
CREATE TABLE IF NOT EXISTS task_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_name TEXT NOT NULL,
    run_id INTEGER REFERENCES task_runs(id),
    occurred_at TEXT NOT NULL,
    error_type TEXT NOT NULL,
    error_message TEXT,
    stderr_output TEXT,
    notified INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS remediation_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_name TEXT NOT NULL,
    error_id INTEGER REFERENCES task_errors(id),
    run_session_id TEXT,
    remediation_session_id TEXT,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    investigation TEXT,
    resolution TEXT,
    resolved_at TEXT,
    user_guidance TEXT
);
CREATE TABLE IF NOT EXISTS task_state (
    task_name TEXT PRIMARY KEY,
    last_run_at TEXT,
    last_status TEXT,
    consecutive_failures INTEGER DEFAULT 0,
    total_runs INTEGER DEFAULT 0,
    total_failures INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_name TEXT,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    read INTEGER DEFAULT 0,
    action_cmd TEXT
);
"""

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        # Migrations — add cost columns to existing databases
        for col, typ in [("input_tokens", "INTEGER DEFAULT 0"),
                         ("output_tokens", "INTEGER DEFAULT 0"),
                         ("cost_usd", "REAL DEFAULT 0.0")]:
            try:
                self.execute(f"ALTER TABLE task_runs ADD COLUMN {col} {typ}")
                self.conn.commit()
            except Exception:
                pass  # Column already exists

        # Migrations — add security model tables
        for create_sql in [
            """CREATE TABLE IF NOT EXISTS context_artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT NOT NULL,
                run_id INTEGER REFERENCES task_runs(id),
                created_at TEXT NOT NULL,
                artifact_type TEXT NOT NULL,
                content TEXT NOT NULL,
                consumed_by_run_id INTEGER
            )""",
            """CREATE TABLE IF NOT EXISTS pending_approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT NOT NULL,
                artifact_id INTEGER REFERENCES context_artifacts(id),
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                reviewed_at TEXT,
                reviewer_note TEXT
            )""",
        ]:
            try:
                self.execute(create_sql)
                self.conn.commit()
            except Exception:
                pass

    def execute(self, sql, params=()):
        return self.conn.execute(sql, params)

    def close(self):
        self.conn.close()

    # --- Runs ---
    def start_run(self, task_name: str, task_file: str,
                  log_file: str, attempt: int = 1,
                  session_id: str = "") -> int:
        cur = self.execute(
            "INSERT INTO task_runs (task_name, task_file, started_at,"
            " log_file, attempt, session_id)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (task_name, task_file, _now(), log_file, attempt, session_id))
        self.conn.commit()
        return cur.lastrowid

    def complete_run(self, run_id: int, status: str,
                     exit_code: int = None, error_message: str = ""):
        row = self.execute("SELECT started_at FROM task_runs WHERE id=?",
                           (run_id,)).fetchone()
        duration = 0.0
        if row:
            start = datetime.fromisoformat(row["started_at"])
            duration = (datetime.now(timezone.utc) - start).total_seconds()
        self.execute(
            "UPDATE task_runs SET status=?, exit_code=?, completed_at=?,"
            " duration_seconds=?, error_message=? WHERE id=?",
            (status, exit_code, _now(), duration, error_message, run_id))
        self.conn.commit()

    def set_run_cost(self, run_id: int, input_tokens: int, output_tokens: int, cost_usd: float):
        self.execute(
            "UPDATE task_runs SET input_tokens=?, output_tokens=?, cost_usd=? WHERE id=?",
            (input_tokens, output_tokens, cost_usd, run_id))
        self.conn.commit()

    def set_run_session_id(self, run_id: int, session_id: str):
        self.execute("UPDATE task_runs SET session_id=? WHERE id=?",
                     (session_id, run_id))
        self.conn.commit()

    def get_run(self, run_id: int) -> RunRecord:
        row = self.execute("SELECT * FROM task_runs WHERE id=?",
                           (run_id,)).fetchone()
        if not row:
            raise ValueError(f"Run {run_id} not found")
        return RunRecord(**dict(row))

    def get_run_history(self, task_name: str = None,
                        limit: int = 20) -> list[RunRecord]:
        if task_name:
            rows = self.execute(
                "SELECT * FROM task_runs WHERE task_name=?"
                " ORDER BY id DESC LIMIT ?", (task_name, limit)).fetchall()
        else:
            rows = self.execute(
                "SELECT * FROM task_runs ORDER BY id DESC LIMIT ?",
                (limit,)).fetchall()
        return [RunRecord(**dict(r)) for r in rows]

    def recover_stale_runs(self, max_age_seconds: int = 3600) -> list[RunRecord]:
        cutoff = (datetime.now(timezone.utc)
                  - timedelta(seconds=max_age_seconds)).isoformat()
        rows = self.execute(
            "SELECT * FROM task_runs WHERE status='running'"
            " AND started_at < ?", (cutoff,)).fetchall()
        stale = [RunRecord(**dict(r)) for r in rows]
        for run in stale:
            self.execute(
                "UPDATE task_runs SET status='crashed', completed_at=? WHERE id=?",
                (_now(), run.id))
        self.conn.commit()
        return stale

    # --- Errors ---
    def record_error(self, task_name: str, run_id: int, error_type: str,
                     error_message: str, stderr_output: str = "") -> int:
        cur = self.execute(
            "INSERT INTO task_errors"
            " (task_name, run_id, occurred_at, error_type, error_message, stderr_output)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (task_name, run_id, _now(), error_type, error_message, stderr_output))
        self.conn.commit()
        return cur.lastrowid

    def get_errors(self, task_name: str = None,
                   limit: int = 20) -> list[ErrorRecord]:
        if task_name:
            rows = self.execute(
                "SELECT * FROM task_errors WHERE task_name=?"
                " ORDER BY id DESC LIMIT ?", (task_name, limit)).fetchall()
        else:
            rows = self.execute(
                "SELECT * FROM task_errors ORDER BY id DESC LIMIT ?",
                (limit,)).fetchall()
        return [ErrorRecord(**dict(r)) for r in rows]

    # --- Task State ---
    def update_task_state(self, task_name: str, status: str):
        existing = self.execute(
            "SELECT * FROM task_state WHERE task_name=?",
            (task_name,)).fetchone()
        now = _now()
        if existing:
            consec = existing["consecutive_failures"]
            consec = consec + 1 if status == "failed" else 0
            total_f = existing["total_failures"] + (1 if status == "failed" else 0)
            self.execute(
                "UPDATE task_state SET last_run_at=?, last_status=?,"
                " consecutive_failures=?, total_runs=total_runs+1,"
                " total_failures=? WHERE task_name=?",
                (now, status, consec, total_f, task_name))
        else:
            self.execute(
                "INSERT INTO task_state VALUES (?, ?, ?, ?, 1, ?)",
                (task_name, now, status,
                 1 if status == "failed" else 0,
                 1 if status == "failed" else 0))
        self.conn.commit()

    def get_task_state(self, task_name: str) -> dict | None:
        row = self.execute("SELECT * FROM task_state WHERE task_name=?",
                           (task_name,)).fetchone()
        return dict(row) if row else None

    def get_all_task_states(self) -> list[dict]:
        rows = self.execute("SELECT * FROM task_state ORDER BY task_name").fetchall()
        return [dict(r) for r in rows]

    # --- Tickets ---
    def create_ticket(self, task_name: str, error_id: int,
                      investigation: str = "",
                      run_session_id: str = "",
                      remediation_session_id: str = "") -> int:
        cur = self.execute(
            "INSERT INTO remediation_tickets"
            " (task_name, error_id, created_at, investigation,"
            "  run_session_id, remediation_session_id)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (task_name, error_id, _now(), investigation,
             run_session_id, remediation_session_id))
        self.conn.commit()
        return cur.lastrowid

    def get_ticket(self, ticket_id: int) -> Ticket:
        row = self.execute(
            "SELECT * FROM remediation_tickets WHERE id=?",
            (ticket_id,)).fetchone()
        if not row:
            raise ValueError(f"Ticket {ticket_id} not found")
        return Ticket(**dict(row))

    def get_tickets(self, status: str = None) -> list[Ticket]:
        if status:
            rows = self.execute(
                "SELECT * FROM remediation_tickets WHERE status=?"
                " ORDER BY id DESC", (status,)).fetchall()
        else:
            rows = self.execute(
                "SELECT * FROM remediation_tickets ORDER BY id DESC"
            ).fetchall()
        return [Ticket(**dict(r)) for r in rows]

    def update_ticket(self, ticket_id: int, **kwargs):
        if "status" in kwargs and kwargs["status"] == "resolved":
            kwargs["resolved_at"] = _now()
        sets = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [ticket_id]
        self.execute(f"UPDATE remediation_tickets SET {sets} WHERE id=?", vals)
        self.conn.commit()

    # --- Notifications ---
    def log_notification(self, task_name: str, severity: str, title: str,
                         message: str, action_cmd: str = "") -> int:
        cur = self.execute(
            "INSERT INTO notifications (task_name, severity, title, message, sent_at, action_cmd)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (task_name, severity, title, message, _now(), action_cmd))
        self.conn.commit()
        return cur.lastrowid

    def get_notifications(self, unread_only: bool = True,
                          limit: int = 50) -> list[dict]:
        if unread_only:
            rows = self.execute(
                "SELECT * FROM notifications WHERE read=0"
                " ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        else:
            rows = self.execute(
                "SELECT * FROM notifications ORDER BY id DESC LIMIT ?",
                (limit,)).fetchall()
        return [dict(r) for r in rows]

    def mark_notifications_read(self):
        self.execute("UPDATE notifications SET read=1 WHERE read=0")
        self.conn.commit()

    # --- Context Artifacts ---
    def create_artifact(self, task_name: str, run_id: int,
                        artifact_type: str, content: str) -> int:
        cur = self.execute(
            "INSERT INTO context_artifacts (task_name, run_id, created_at, artifact_type, content)"
            " VALUES (?, ?, ?, ?, ?)",
            (task_name, run_id, _now(), artifact_type, content))
        self.conn.commit()
        return cur.lastrowid

    def get_artifact(self, artifact_id: int) -> dict:
        row = self.execute(
            "SELECT * FROM context_artifacts WHERE id=?", (artifact_id,)).fetchone()
        return dict(row) if row else None

    def get_artifacts(self, task_name: str) -> list[dict]:
        rows = self.execute(
            "SELECT * FROM context_artifacts WHERE task_name=? ORDER BY id DESC",
            (task_name,)).fetchall()
        return [dict(r) for r in rows]

    # --- Pending Approvals ---
    def create_approval(self, task_name: str, artifact_id: int) -> int:
        cur = self.execute(
            "INSERT INTO pending_approvals (task_name, artifact_id, created_at) VALUES (?, ?, ?)",
            (task_name, artifact_id, _now()))
        self.conn.commit()
        return cur.lastrowid

    def get_pending_approvals(self) -> list[dict]:
        rows = self.execute(
            "SELECT * FROM pending_approvals WHERE status='pending' ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]

    def update_approval(self, approval_id: int, status: str, note: str = ""):
        self.execute(
            "UPDATE pending_approvals SET status=?, reviewed_at=?, reviewer_note=? WHERE id=?",
            (status, _now(), note, approval_id))
        self.conn.commit()
