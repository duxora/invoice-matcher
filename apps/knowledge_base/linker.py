"""Suggest links between related notes."""

import sqlite3
from pathlib import Path


class NotesLinker:
    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row

    def find_related(self, note_path: str, limit: int = 5) -> list[dict]:
        note = self.conn.execute(
            "SELECT id, title, tags FROM notes WHERE path = ?", (note_path,)
        ).fetchone()
        if not note:
            return []
        # Search by title keywords
        keywords = " OR ".join(note["title"].split())
        if not keywords:
            return []
        try:
            rows = self.conn.execute(
                "SELECT n.path, n.title, "
                "snippet(notes_fts, 1, '**', '**', '...', 20) as snippet "
                "FROM notes_fts f JOIN notes n ON f.rowid = n.id "
                "WHERE notes_fts MATCH ? AND n.path != ? "
                "ORDER BY rank LIMIT ?",
                (keywords, note_path, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def suggest_links(self, limit: int = 20) -> list[dict]:
        notes = self.conn.execute(
            "SELECT path, title FROM notes LIMIT 100"
        ).fetchall()
        suggestions = []
        seen: set[tuple[str, str]] = set()
        for note in notes:
            related = self.find_related(note["path"], limit=3)
            for r in related:
                pair = tuple(sorted([note["path"], r["path"]]))
                if pair not in seen:
                    seen.add(pair)
                    suggestions.append(
                        {
                            "from": note["path"],
                            "from_title": note["title"],
                            "to": r["path"],
                            "to_title": r["title"],
                        }
                    )
            if len(suggestions) >= limit:
                break
        return suggestions[:limit]
