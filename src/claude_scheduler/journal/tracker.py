"""SQLite tracker for journal progress."""
import sqlite3
from pathlib import Path


class JournalTracker:
    """Track journal sessions and compute statistics."""

    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS journal_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                prompt TEXT,
                text TEXT,
                grammar_score INTEGER,
                vocab_score INTEGER,
                reasoning_score INTEGER,
                word_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def record_session(self, date: str, prompt: str, text: str,
                       grammar_score: int, vocab_score: int,
                       reasoning_score: int, word_count: int):
        """Record a journal session, replacing any existing entry for the date."""
        self.conn.execute(
            "INSERT OR REPLACE INTO journal_sessions "
            "(date, prompt, text, grammar_score, vocab_score, reasoning_score, word_count) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (date, prompt, text, grammar_score, vocab_score, reasoning_score, word_count),
        )
        self.conn.commit()

    def get_stats(self) -> dict:
        """Return aggregate statistics across all sessions."""
        row = self.conn.execute(
            "SELECT COUNT(*) as total, "
            "AVG(grammar_score) as avg_grammar, "
            "AVG(vocab_score) as avg_vocab, "
            "AVG(reasoning_score) as avg_reasoning, "
            "AVG(word_count) as avg_words "
            "FROM journal_sessions"
        ).fetchone()
        return {
            "total_sessions": row["total"],
            "avg_grammar": round(row["avg_grammar"] or 0, 1),
            "avg_vocab": round(row["avg_vocab"] or 0, 1),
            "avg_reasoning": round(row["avg_reasoning"] or 0, 1),
            "avg_words": round(row["avg_words"] or 0, 1),
        }

    def get_streak(self) -> int:
        """Return the current consecutive-day streak ending at the most recent entry."""
        rows = self.conn.execute(
            "SELECT date FROM journal_sessions ORDER BY date DESC"
        ).fetchall()
        if not rows:
            return 0
        from datetime import date as dt_date, timedelta
        dates = [dt_date.fromisoformat(r["date"]) for r in rows]
        streak = 1
        for i in range(1, len(dates)):
            if dates[i - 1] - dates[i] == timedelta(days=1):
                streak += 1
            else:
                break
        return streak
