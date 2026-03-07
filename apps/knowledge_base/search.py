"""Search notes using FTS5 full-text search."""

import sqlite3
from pathlib import Path


class VaultSearch:
    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row

    def search(self, query: str, limit: int = 10) -> list[dict]:
        rows = self.conn.execute(
            "SELECT n.path, n.title, n.word_count, n.tags, "
            "snippet(notes_fts, 1, '**', '**', '...', 30) as snippet "
            "FROM notes_fts f JOIN notes n ON f.rowid = n.id "
            "WHERE notes_fts MATCH ? ORDER BY rank LIMIT ?",
            (query, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_note(self, path: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM notes WHERE path = ?", (path,)
        ).fetchone()
        return dict(row) if row else None
