"""Tests for demo recorder."""
import pytest

from claude_scheduler.demo.scripts import get_demo_script, list_demos, DEMO_SCRIPTS
from claude_scheduler.demo.recorder import (
    get_output_dir,
    generate_output_path,
    AsciinemaBackend,
    ScriptBackend,
)
from claude_scheduler.demo.runner import _run_step


def test_demo_scripts_exist():
    assert len(DEMO_SCRIPTS) >= 6
    assert "workflow" in DEMO_SCRIPTS
    assert "debate" in DEMO_SCRIPTS
    assert "journal" in DEMO_SCRIPTS


def test_get_demo_script():
    script = get_demo_script("workflow")
    assert "steps" in script
    assert len(script["steps"]) > 0


def test_invalid_demo_raises():
    with pytest.raises(ValueError):
        get_demo_script("nonexistent")


def test_list_demos():
    demos = list_demos()
    assert len(demos) >= 6
    assert all("key" in d and "name" in d for d in demos)


def test_generate_output_path():
    path = generate_output_path("test")
    assert "demo-test-" in str(path)


def test_output_dir_creation(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    from claude_scheduler.demo.recorder import get_output_dir
    output = get_output_dir()
    assert output.exists()


def test_asciinema_availability():
    result = AsciinemaBackend.is_available()
    assert isinstance(result, bool)


def test_script_availability():
    result = ScriptBackend.is_available()
    assert isinstance(result, bool)


def test_run_step_type(capsys):
    _run_step(("type", "hello"), workdir="")
    # type writes to stdout character by character
    # capsys may not capture all due to flush, but shouldn't crash


def test_run_step_header(capsys):
    _run_step(("header", "Test Header"), workdir="")
    captured = capsys.readouterr()
    assert "Test Header" in captured.out


def test_run_step_cmd():
    # Run a simple, safe command
    _run_step(("cmd", "echo 'demo test'"), workdir="")
    # Should not raise
