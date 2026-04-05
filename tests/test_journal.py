"""Tests for the daily journal module."""
from claude_scheduler.journal.daily import get_daily_prompt, PROMPT_BANK
from claude_scheduler.journal.reviewer import build_review_prompt
from claude_scheduler.journal.tracker import JournalTracker


def test_prompt_bank_not_empty():
    assert len(PROMPT_BANK) >= 10


def test_get_daily_prompt_returns_string():
    prompt = get_daily_prompt()
    assert isinstance(prompt, str)
    assert len(prompt) > 10


def test_get_daily_prompt_deterministic():
    from datetime import date
    p1 = get_daily_prompt(date(2026, 3, 7))
    p2 = get_daily_prompt(date(2026, 3, 7))
    assert p1 == p2


def test_get_daily_prompt_varies_by_date():
    from datetime import date
    prompts = set()
    for day in range(1, 15):
        prompts.add(get_daily_prompt(date(2026, 3, day)))
    assert len(prompts) > 1  # not all the same


def test_build_review_prompt():
    text = "I think microservices are better because they scale independently."
    prompt = build_review_prompt(text)
    assert "grammar" in prompt.lower()
    assert "reasoning" in prompt.lower() or "logic" in prompt.lower()
    assert "microservices" in prompt


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


def test_tracker_broken_streak(tmp_path):
    tracker = JournalTracker(tmp_path / "journal.db")
    tracker.record_session("2026-03-04", "p", "t", 3, 3, 3, 100)
    # gap on 2026-03-05
    tracker.record_session("2026-03-06", "p", "t", 4, 4, 4, 120)
    tracker.record_session("2026-03-07", "p", "t", 4, 4, 4, 130)
    assert tracker.get_streak() == 2
