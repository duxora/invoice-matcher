from unittest.mock import patch

from apps.speaking_coach.evaluator import build_eval_prompt, parse_evaluation
from apps.speaking_coach.progress import SpeakingTracker
from apps.speaking_coach.scenarios import SCENARIOS, get_scenario, list_scenarios
from apps.speaking_coach.session import SpeakingSession
from apps.voice_input.recorder import record_and_transcribe  # noqa: F401
from apps.voice_input.refiner import REFINE_PROMPT, refine_transcript  # noqa: F401


# --- Scenarios ---
def test_scenarios_exist():
    assert len(SCENARIOS) >= 5
    assert "standup" in SCENARIOS
    assert "interview" in SCENARIOS
    assert "free" in SCENARIOS


def test_get_scenario():
    s = get_scenario("standup")
    assert "opening" in s
    assert "standup" in s["name"].lower()


def test_invalid_scenario():
    import pytest

    with pytest.raises(ValueError):
        get_scenario("nonexistent")


def test_list_scenarios():
    scenarios = list_scenarios()
    assert len(scenarios) >= 5
    assert all("key" in s for s in scenarios)


# --- Evaluator ---
def test_build_eval_prompt():
    prompt = build_eval_prompt("I working on bug fix yesterday", "Daily Standup")
    assert "I working on bug fix yesterday" in prompt
    assert "grammar" in prompt.lower()


def test_parse_evaluation_valid():
    raw = (
        '{"grammar_score": 3, "grammar_corrections": ["worked, not working"], '
        '"vocabulary_score": 4, "vocabulary_suggestions": [], '
        '"fluency_score": 3, "fluency_feedback": "Good", '
        '"overall_score": 3.3, "natural_response": "Thanks!", "tip": "Use past tense."}'
    )
    ev = parse_evaluation(raw)
    assert ev["grammar_score"] == 3
    assert ev["overall_score"] == 3.3


def test_parse_evaluation_invalid():
    ev = parse_evaluation("broken")
    assert ev["overall_score"] == 0


# --- Progress ---
def test_tracker_record_and_progress(tmp_path):
    tracker = SpeakingTracker(tmp_path / "speak.db")
    tracker.record_session("2026-03-07", "standup", 5, 3.5, 4.0, 3.0, 3.5)
    progress = tracker.get_progress()
    assert progress["total_sessions"] == 1
    assert progress["avg_grammar"] == 3.5
    assert progress["total_turns"] == 5


# --- Session ---
@patch("apps.speaking_coach.session.subprocess.run")
def test_session_opening(mock_run):
    session = SpeakingSession(scenario="standup")
    opening = session.get_opening()
    assert "standup" in opening.lower() or "yesterday" in opening.lower()


@patch("apps.speaking_coach.session.subprocess.run")
def test_session_evaluate(mock_run):
    mock_run.return_value = type(
        "R",
        (),
        {
            "returncode": 0,
            "stdout": b'{"result": "{\\"grammar_score\\": 4, \\"vocabulary_score\\": 3, \\"fluency_score\\": 4, \\"overall_score\\": 3.7, \\"grammar_corrections\\": [], \\"vocabulary_suggestions\\": [], \\"fluency_feedback\\": \\"Good\\", \\"natural_response\\": \\"Nice\\", \\"tip\\": \\"Keep going\\"}"}',
            "stderr": b"",
        },
    )()
    session = SpeakingSession(scenario="free")
    ev = session.evaluate_response("I think AI is very useful for learning")
    assert session.turn_count == 1


# --- Voice (import test only, no audio hardware) ---
def test_voice_refiner_prompt():
    assert "transcript" in REFINE_PROMPT.lower()
