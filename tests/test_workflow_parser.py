"""Tests for workflow parser."""

from pathlib import Path

from claude_scheduler.workflow.parser import find_workflows, parse_workflow

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_workflow():
    wf = parse_workflow(FIXTURES / "sample.workflow")
    assert wf.name == "Daily Code Quality Check"
    assert wf.trigger == "daily 09:00"
    assert len(wf.steps) == 4
    assert wf.steps[0].description == "Pull latest changes from main branch"
    assert wf.steps[3].description == "Summarize findings"
    assert wf.security_level == "medium"
    assert "Bash(git, ruff)" in wf.allowed_tools
    assert wf.on_failure == "retry_once"


def test_parse_workflow_missing_file():
    import pytest

    with pytest.raises(FileNotFoundError):
        parse_workflow(Path("/nonexistent.workflow"))


def test_parse_workflow_minimal():
    import tempfile

    content = "# My Task\n\n## Trigger\nschedule: every 2h\n\n## Steps\n1. Do something\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".workflow", delete=False) as f:
        f.write(content)
        path = Path(f.name)
    try:
        wf = parse_workflow(path)
        assert wf.name == "My Task"
        assert wf.trigger == "every 2h"
        assert len(wf.steps) == 1
    finally:
        path.unlink()


def test_find_workflows(tmp_path):
    (tmp_path / "a.workflow").write_text(
        "# A\n\n## Trigger\nschedule: daily 09:00\n\n## Steps\n1. Do A\n"
    )
    (tmp_path / "b.workflow").write_text(
        "# B\n\n## Trigger\nschedule: daily 10:00\n\n## Steps\n1. Do B\n"
    )
    (tmp_path / "not-a-workflow.txt").write_text("ignore me")
    workflows = find_workflows(tmp_path)
    assert len(workflows) == 2
