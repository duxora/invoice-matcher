"""Scan Obsidian vault and build a local search index."""

import hashlib
import re
import sqlite3
from pathlib import Path


class VaultIndexer:
    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                title TEXT,
                content TEXT,
                content_hash TEXT,
                word_count INTEGER,
                tags TEXT DEFAULT '',
                links TEXT DEFAULT '',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts
            USING fts5(title, content, tags, content='notes', content_rowid='id')
        """)
        self.conn.commit()

    def index_vault(self, vault_path: Path) -> dict:
        vault_path = Path(vault_path)
        stats = {"indexed": 0, "skipped": 0, "errors": 0}
        for md_file in vault_path.rglob("*.md"):
            try:
                content = md_file.read_text(errors="replace")
                content_hash = hashlib.md5(content.encode()).hexdigest()

                existing = self.conn.execute(
                    "SELECT content_hash FROM notes WHERE path = ?",
                    (str(md_file),),
                ).fetchone()
                if existing and existing["content_hash"] == content_hash:
                    stats["skipped"] += 1
                    continue

                title = md_file.stem
                # Extract tags from frontmatter or inline
                tags = ",".join(
                    word.lstrip("#")
                    for word in content.split()
                    if word.startswith("#")
                    and len(word) > 1
                    and not word.startswith("##")
                )
                # Extract wiki-style links
                links = ",".join(re.findall(r"\[\[([^\]]+)\]\]", content))
                word_count = len(content.split())

                self.conn.execute(
                    "INSERT OR REPLACE INTO notes "
                    "(path, title, content, content_hash, word_count, tags, links) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (str(md_file), title, content, content_hash, word_count, tags, links),
                )
                stats["indexed"] += 1
            except Exception:
                stats["errors"] += 1
        self.conn.commit()
        # Rebuild FTS index
        self.conn.execute("INSERT INTO notes_fts(notes_fts) VALUES('rebuild')")
        self.conn.commit()
        return stats

    def get_stats(self) -> dict:
        row = self.conn.execute(
            "SELECT COUNT(*) as total, SUM(word_count) as total_words FROM notes"
        ).fetchone()
        return {"total_notes": row["total"], "total_words": row["total_words"] or 0}
