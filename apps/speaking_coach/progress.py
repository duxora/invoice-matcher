"""SQLite tracker for speaking practice progress."""
import sqlite3
from pathlib import Path


class SpeakingTracker:
    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS speaking_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                scenario TEXT,
                turns INTEGER DEFAULT 0,
                grammar_avg REAL DEFAULT 0,
                vocabulary_avg REAL DEFAULT 0,
                fluency_avg REAL DEFAULT 0,
                overall_avg REAL DEFAULT 0,
                new_vocabulary TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def record_session(
        self,
        date: str,
        scenario: str,
        turns: int,
        grammar_avg: float,
        vocabulary_avg: float,
        fluency_avg: float,
        overall_avg: float,
        new_vocabulary: str = "",
    ):
        self.conn.execute(
            "INSERT INTO speaking_sessions "
            "(date, scenario, turns, grammar_avg, vocabulary_avg, fluency_avg, overall_avg, new_vocabulary) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (date, scenario, turns, grammar_avg, vocabulary_avg, fluency_avg, overall_avg, new_vocabulary),
        )
        self.conn.commit()

    def get_progress(self) -> dict:
        row = self.conn.execute(
            "SELECT COUNT(*) as total, "
            "AVG(grammar_avg) as grammar, AVG(vocabulary_avg) as vocab, "
            "AVG(fluency_avg) as fluency, AVG(overall_avg) as overall, "
            "SUM(turns) as total_turns "
            "FROM speaking_sessions"
        ).fetchone()
        return {
            "total_sessions": row["total"],
            "avg_grammar": round(row["grammar"] or 0, 1),
            "avg_vocabulary": round(row["vocab"] or 0, 1),
            "avg_fluency": round(row["fluency"] or 0, 1),
            "avg_overall": round(row["overall"] or 0, 1),
            "total_turns": row["total_turns"] or 0,
        }
