from unittest.mock import patch

from apps.socratic_bot.modes import get_system_prompt, MODES
from apps.socratic_bot.debate import DebateSession
from apps.socratic_bot.scorer import build_scoring_prompt, parse_score


# --- Modes ---
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


# --- Debate ---
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


# --- Scorer ---
def test_build_scoring_prompt():
    history = [
        {"role": "user", "content": "AI will replace developers"},
        {"role": "assistant", "content": "Why?"},
        {"role": "user", "content": "Because AI writes code faster"},
    ]
    prompt = build_scoring_prompt(history)
    assert "AI will replace developers" in prompt
    assert "logic" in prompt.lower() or "reasoning" in prompt.lower()


def test_parse_score_valid():
    raw = '{"logic": 3, "evidence": 2, "counterarguments": 1, "clarity": 4, "overall": 2.5, "feedback": "Needs more evidence."}'
    score = parse_score(raw)
    assert score["logic"] == 3
    assert score["overall"] == 2.5
    assert "feedback" in score


def test_parse_score_invalid():
    score = parse_score("not json")
    assert score["overall"] == 0
