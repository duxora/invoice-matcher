# Phases 2-5: Personal Dev Apps — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build Socratic debate bot, daily journal, speaking coach, voice input, knowledge base, and SOP converter.

**Architecture:** Standalone apps under `apps/` and modules under `src/claude_scheduler/`. All use Claude CLI via existing executor infrastructure.

**Tech Stack:** Python 3.12, speech_recognition, edge-tts, pynput, numpy, SQLite

---

## Phase 2: Socratic Debate Bot + Daily Journal (text-only, no audio deps)

### Task 1: Socratic Bot — Debate Modes + System Prompts

**Files:**
- Create: `apps/socratic-bot/__init__.py`
- Create: `apps/socratic-bot/modes.py`
- Test: `tests/test_socratic_modes.py`

**Step 1: Write failing test**

```python
# tests/test_socratic_modes.py
from apps.socratic_bot.modes import get_system_prompt, MODES

def test_modes_exist():
    assert "socratic" in MODES
    assert "devil" in MODES
    assert "steelman" in MODES

def test_system_prompt_contains_mode_instruction():
    prompt = get_system_prompt("socratic")
    assert "why" in prompt.lower()
    assert "assumption" in prompt.lower()

def test_system_prompt_devil():
    prompt = get_system_prompt("devil")
    assert "opposite" in prompt.lower()

def test_invalid_mode_raises():
    import pytest
    with pytest.raises(ValueError):
        get_system_prompt("nonexistent")
```

**Step 2: Run test, verify fails**

Run: `python -m pytest tests/test_socratic_modes.py -v`

**Step 3: Write implementation**

```python
# apps/socratic-bot/__init__.py (renamed from socratic_bot for imports)
# Note: directory is apps/socratic-bot/ but Python package is apps.socratic_bot

# apps/socratic-bot/modes.py
MODES = {
    "socratic": {
        "name": "Socratic Questioning",
        "prompt": (
            "You are a Socratic questioning partner. Your role is to help the user "
            "sharpen their thinking through probing questions. Rules:\n"
            "- Never give direct answers or opinions\n"
            "- Ask ONE question at a time that exposes assumptions\n"
            "- Use 'why do you think that?' and 'what if the opposite were true?'\n"
            "- When the user makes a claim, ask for evidence or reasoning\n"
            "- Identify logical fallacies gently by asking clarifying questions\n"
            "- Summarize the user's position before challenging it\n"
            "- Keep responses under 100 words\n"
        ),
    },
    "devil": {
        "name": "Devil's Advocate",
        "prompt": (
            "You are a devil's advocate debater. Your role is to argue the opposite "
            "position of whatever the user claims. Rules:\n"
            "- Always take the opposite side, even if you agree\n"
            "- Present strong counterarguments with evidence\n"
            "- Be respectful but relentless\n"
            "- If the user switches sides, switch too\n"
            "- Acknowledge strong points before countering\n"
            "- Keep responses under 150 words\n"
        ),
    },
    "steelman": {
        "name": "Steelman",
        "prompt": (
            "You are a steelman debate partner. Your role is to first strengthen "
            "the user's argument to its best possible version, then find remaining "
            "weaknesses. Rules:\n"
            "- First, restate the user's argument in its strongest form\n"
            "- Add supporting evidence they may have missed\n"
            "- Then identify the 1-2 weakest remaining points\n"
            "- Suggest how to address those weaknesses\n"
            "- Keep responses under 200 words\n"
        ),
    },
}

def get_system_prompt(mode: str) -> str:
    if mode not in MODES:
        raise ValueError(f"Unknown mode: {mode}. Available: {', '.join(MODES)}")
    return MODES[mode]["prompt"]
```

**Step 4: Run tests, verify pass**

**Step 5: Commit**

```bash
git commit -m "feat(socratic): add debate modes with system prompts"
```

---

### Task 2: Socratic Bot — Debate Session Loop

**Files:**
- Create: `apps/socratic-bot/debate.py`
- Test: `tests/test_socratic_debate.py`

**Step 1: Write failing test**

```python
# tests/test_socratic_debate.py
from unittest.mock import patch
from apps.socratic_bot.debate import DebateSession

@patch("apps.socratic_bot.debate.subprocess.run")
def test_debate_session_sends_prompt(mock_run):
    mock_run.return_value = type("R", (), {
        "returncode": 0,
        "stdout": b'{"result": "Why do you think that?", "session_id": "s1"}',
        "stderr": b"",
    })()
    session = DebateSession(mode="socratic")
    response = session.send("Microservices are always better than monoliths")
    assert response is not None
    assert session.turn_count == 1

@patch("apps.socratic_bot.debate.subprocess.run")
def test_debate_session_tracks_turns(mock_run):
    mock_run.return_value = type("R", (), {
        "returncode": 0,
        "stdout": b'{"result": "Interesting.", "session_id": "s1"}',
        "stderr": b"",
    })()
    session = DebateSession(mode="devil")
    session.send("AI will replace all developers")
    session.send("Because AI can write code faster")
    assert session.turn_count == 2
```

**Step 2: Run test, verify fails**

**Step 3: Write implementation**

```python
# apps/socratic-bot/debate.py
"""Interactive debate session using Claude CLI."""
import json
import subprocess
from .modes import get_system_prompt

class DebateSession:
    def __init__(self, mode: str = "socratic", model: str = "claude-sonnet-4-6"):
        self.mode = mode
        self.model = model
        self.system_prompt = get_system_prompt(mode)
        self.session_id = ""
        self.turn_count = 0
        self.history: list[dict] = []

    def send(self, message: str) -> str:
        cmd = [
            "claude", "-p",
            f"{self.system_prompt}\n\nUser says: {message}",
            "--model", self.model,
            "--output-format", "json",
        ]
        if self.session_id:
            cmd.extend(["--resume", self.session_id])

        proc = subprocess.run(cmd, capture_output=True, timeout=120)
        stdout = proc.stdout.decode(errors="replace")

        try:
            data = json.loads(stdout)
            response = data.get("result", stdout)
            self.session_id = data.get("session_id", self.session_id)
        except json.JSONDecodeError:
            response = stdout

        self.turn_count += 1
        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": response})
        return response

    def summary(self) -> dict:
        return {
            "mode": self.mode,
            "turns": self.turn_count,
            "session_id": self.session_id,
        }
```

**Step 4: Run tests, verify pass**

**Step 5: Commit**

```bash
git commit -m "feat(socratic): add interactive debate session loop"
```

---

### Task 3: Socratic Bot — Argument Scorer

**Files:**
- Create: `apps/socratic-bot/scorer.py`
- Test: `tests/test_socratic_scorer.py`

**Step 1: Write failing test**

```python
# tests/test_socratic_scorer.py
from apps.socratic_bot.scorer import build_scoring_prompt, parse_score

def test_build_scoring_prompt():
    history = [
        {"role": "user", "content": "AI will replace developers"},
        {"role": "assistant", "content": "Why?"},
        {"role": "user", "content": "Because AI writes code faster"},
    ]
    prompt = build_scoring_prompt(history)
    assert "AI will replace developers" in prompt
    assert "logical" in prompt.lower() or "reasoning" in prompt.lower()

def test_parse_score_valid():
    raw = '{"logic": 3, "evidence": 2, "counterarguments": 1, "clarity": 4, "overall": 2.5, "feedback": "Needs more evidence."}'
    score = parse_score(raw)
    assert score["logic"] == 3
    assert score["overall"] == 2.5
    assert "feedback" in score

def test_parse_score_invalid():
    score = parse_score("not json")
    assert score["overall"] == 0
```

**Step 3: Write implementation**

```python
# apps/socratic-bot/scorer.py
"""Score argument quality from debate history."""
import json

SCORING_PROMPT = """\
Evaluate the USER's argumentation quality in this debate. Score 1-5 for each:

Debate transcript:
{transcript}

Return ONLY JSON:
{{"logic": <1-5>, "evidence": <1-5>, "counterarguments": <1-5>, "clarity": <1-5>, "overall": <1.0-5.0>, "feedback": "<2 sentences>"}}
"""

def build_scoring_prompt(history: list[dict]) -> str:
    transcript = "\n".join(
        f"{'User' if h['role'] == 'user' else 'Bot'}: {h['content']}"
        for h in history
    )
    return SCORING_PROMPT.format(transcript=transcript)

def parse_score(raw: str) -> dict:
    try:
        # Handle claude JSON wrapper
        try:
            data = json.loads(raw)
            if "result" in data:
                return json.loads(data["result"])
            return data
        except (json.JSONDecodeError, TypeError):
            pass
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {"logic": 0, "evidence": 0, "counterarguments": 0,
                "clarity": 0, "overall": 0, "feedback": "Could not parse score."}
```

**Step 4: Run tests, verify pass**

**Step 5: Commit**

```bash
git commit -m "feat(socratic): add argument quality scorer"
```

---

### Task 4: Daily Journal — Core Module

**Files:**
- Create: `src/claude_scheduler/journal/__init__.py`
- Create: `src/claude_scheduler/journal/daily.py`
- Create: `src/claude_scheduler/journal/reviewer.py`
- Create: `src/claude_scheduler/journal/tracker.py`
- Test: `tests/test_journal.py`

**Step 1: Write failing test**

```python
# tests/test_journal.py
from claude_scheduler.journal.daily import get_daily_prompt, PROMPT_BANK
from claude_scheduler.journal.reviewer import build_review_prompt
from claude_scheduler.journal.tracker import JournalTracker

def test_prompt_bank_not_empty():
    assert len(PROMPT_BANK) >= 10

def test_get_daily_prompt_returns_string():
    prompt = get_daily_prompt()
    assert isinstance(prompt, str)
    assert len(prompt) > 10

def test_build_review_prompt():
    text = "I think microservices are better because they scale independently."
    prompt = build_review_prompt(text)
    assert "grammar" in prompt.lower()
    assert "logic" in prompt.lower() or "reasoning" in prompt.lower()

def test_tracker_record_and_stats(tmp_path):
    tracker = JournalTracker(tmp_path / "journal.db")
    tracker.record_session(
        date="2026-03-07",
        prompt="Discuss AI ethics",
        text="AI should be regulated...",
        grammar_score=4, vocab_score=3, reasoning_score=4,
        word_count=150,
    )
    stats = tracker.get_stats()
    assert stats["total_sessions"] == 1
    assert stats["avg_grammar"] == 4.0

def test_tracker_streak(tmp_path):
    tracker = JournalTracker(tmp_path / "journal.db")
    tracker.record_session("2026-03-05", "p", "t", 3, 3, 3, 100)
    tracker.record_session("2026-03-06", "p", "t", 4, 4, 4, 120)
    tracker.record_session("2026-03-07", "p", "t", 4, 4, 4, 130)
    assert tracker.get_streak() == 3
```

**Step 3: Write implementation**

```python
# src/claude_scheduler/journal/__init__.py
# Daily reflection & argumentation journal.

# src/claude_scheduler/journal/daily.py
"""Daily prompt generator."""
import random
from datetime import date

PROMPT_BANK = [
    "Should AI development be regulated by governments? Argue your position.",
    "Is remote work better than office work for software teams? Defend your view.",
    "Describe a technical decision you made recently. What were the trade-offs?",
    "Should developers be responsible for the ethical implications of their code?",
    "Is test-driven development always worth the extra effort? Why or why not?",
    "Compare microservices vs monolith architecture. When would you choose each?",
    "Should programming languages enforce strict typing? Argue your position.",
    "Is open source software sustainable as a business model?",
    "Describe a time you were wrong about a technical assumption. What did you learn?",
    "Should AI be used in hiring decisions? What safeguards are needed?",
    "Is perfectionism helpful or harmful in software engineering?",
    "Should companies require return-to-office? What does the evidence show?",
    "Describe your ideal development workflow. Why does each part matter?",
    "Is the current pace of AI advancement sustainable and safe?",
    "Should junior developers use AI coding assistants? What are the risks?",
]

def get_daily_prompt(specific_date: date | None = None) -> str:
    d = specific_date or date.today()
    random.seed(d.toordinal())
    return random.choice(PROMPT_BANK)

# src/claude_scheduler/journal/reviewer.py
"""Claude-powered writing and reasoning review."""

REVIEW_PROMPT = """\
Review this journal entry for BOTH English quality and critical thinking.

Entry:
---
{text}
---

Return ONLY JSON:
{{
  "grammar_score": <1-5>,
  "grammar_issues": ["issue1", "issue2"],
  "vocabulary_score": <1-5>,
  "vocabulary_suggestions": ["word1 -> better_word1"],
  "reasoning_score": <1-5>,
  "reasoning_feedback": "brief feedback on argument quality",
  "logical_fallacies": ["fallacy if any"],
  "socratic_questions": ["follow-up question 1", "follow-up question 2"],
  "overall_feedback": "2-3 sentence summary"
}}
"""

def build_review_prompt(text: str) -> str:
    return REVIEW_PROMPT.format(text=text)

# src/claude_scheduler/journal/tracker.py
"""SQLite tracker for journal progress."""
import sqlite3
from pathlib import Path

class JournalTracker:
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
        self.conn.execute(
            "INSERT OR REPLACE INTO journal_sessions "
            "(date, prompt, text, grammar_score, vocab_score, reasoning_score, word_count) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (date, prompt, text, grammar_score, vocab_score, reasoning_score, word_count),
        )
        self.conn.commit()

    def get_stats(self) -> dict:
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
```

**Step 4: Run tests, verify pass**

**Step 5: Commit**

```bash
git commit -m "feat(journal): add daily prompt, reviewer, and progress tracker"
```

---

### Task 5: CLI Commands for Socratic + Journal

**Files:**
- Modify: `src/claude_scheduler/cli.py`

Add subcommands: `cs debate`, `cs journal`, `cs journal stats`, `cs journal streak`

**Commit:**

```bash
git commit -m "feat(cli): add debate and journal subcommands"
```

---

## Phase 3: Speaking Coach + Voice Input (audio deps)

### Task 6: Voice Shared Infrastructure

**Files:**
- Create: `apps/voice-input/__init__.py`
- Create: `apps/voice-input/recorder.py`

Uses `speech_recognition` + `pyaudio` for STT, `edge-tts` for TTS.

### Task 7: Speaking Coach Session Loop

**Files:**
- Create: `apps/speaking-coach/__init__.py`
- Create: `apps/speaking-coach/session.py`
- Create: `apps/speaking-coach/evaluator.py`
- Create: `apps/speaking-coach/scenarios.py`
- Create: `apps/speaking-coach/progress.py`

### Task 8: Voice-to-Text Refiner

**Files:**
- Create: `apps/voice-input/refiner.py`
- Create: `apps/voice-input/hotkey.py`

**Commits:** One per task (6, 7, 8)

---

## Phase 4: Knowledge Base (Obsidian bridge)

### Task 9: Vault Indexer

**Files:**
- Create: `apps/knowledge-base/__init__.py`
- Create: `apps/knowledge-base/indexer.py`
- Uses numpy for cosine similarity, SQLite for index storage

### Task 10: Search + Synthesizer

**Files:**
- Create: `apps/knowledge-base/search.py`
- Create: `apps/knowledge-base/synthesizer.py`
- Create: `apps/knowledge-base/linker.py`

**Commits:** One per task (9, 10)

---

## Phase 5: SOP Converter

### Task 11: SOP-to-Workflow Converter

**Files:**
- Create: `src/claude_scheduler/workflow/sop_converter.py`
- Test: `tests/test_sop_converter.py`

Calls Claude to parse SOP markdown → outputs `.workflow` file.

**Commit:**

```bash
git commit -m "feat(workflow): add SOP-to-workflow converter"
```
