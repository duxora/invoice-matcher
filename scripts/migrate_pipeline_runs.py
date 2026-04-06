#!/usr/bin/env python3
"""
Migration: create pipeline_runs table in the tkt SQLite DB.
Idempotent — safe to run multiple times.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path.home() / ".backlog" / "backlog.db"


def migrate(db_path: Path = DB_PATH) -> None:
    if not db_path.exists():
        print(f"DB not found at {db_path} — skipping migration")
        return

    with sqlite3.connect(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS pipeline_runs (
              id           INTEGER PRIMARY KEY AUTOINCREMENT,
              task_id      INTEGER NOT NULL,
              session_id   TEXT    NOT NULL,
              pipeline     TEXT    NOT NULL,
              size         TEXT    NOT NULL,
              domain       TEXT,
              started_at   TEXT    NOT NULL,
              completed_at TEXT    NOT NULL,
              duration_s   INTEGER NOT NULL,
              steps        TEXT    NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_pipeline_runs_pipeline
              ON pipeline_runs(pipeline);

            CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started
              ON pipeline_runs(started_at);
        """)
        conn.commit()

    print(f"Migration complete — pipeline_runs table ready in {db_path}")


if __name__ == "__main__":
    migrate()
