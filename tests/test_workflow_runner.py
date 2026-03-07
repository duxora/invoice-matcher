"""Tests for workflow runner — executes steps in sequence with context passing."""
from unittest.mock import patch, MagicMock
from pathlib import Path

from claude_scheduler.workflow.models import Workflow, Step
from claude_scheduler.workflow.runner import WorkflowRunner


def _make_workflow():
    return Workflow(
        name="Test Workflow",
        trigger="daily 09:00",
        steps=[
            Step(order=1, description="List files", tools="Glob"),
            Step(order=2, description="Summarize", tools="Read"),
        ],
        workdir="/tmp",
    )


@patch("claude_scheduler.workflow.runner.execute_task")
def test_runner_executes_steps_in_order(mock_exec):
    mock_exec.return_value = {
        "status": "success", "exit_code": 0, "stdout": "step output",
        "stderr": "", "session_id": "s1", "log_file": "/tmp/log.json",
        "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
    }
    wf = _make_workflow()
    runner = WorkflowRunner(logs_dir=Path("/tmp/logs"))
    result = runner.run(wf)
    assert result["status"] == "success"
    assert mock_exec.call_count == 2
    assert len(result["step_results"]) == 2


@patch("claude_scheduler.workflow.runner.execute_task")
def test_runner_stops_on_failure(mock_exec):
    mock_exec.return_value = {
        "status": "failed", "exit_code": 1, "stdout": "",
        "stderr": "error", "session_id": "", "log_file": "/tmp/log.json",
        "error_message": "Exit code 1",
        "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
    }
    wf = _make_workflow()
    runner = WorkflowRunner(logs_dir=Path("/tmp/logs"))
    result = runner.run(wf)
    assert result["status"] == "failed"
    assert mock_exec.call_count == 1


@patch("claude_scheduler.workflow.runner.execute_task")
def test_runner_passes_context_between_steps(mock_exec):
    mock_exec.return_value = {
        "status": "success", "exit_code": 0, "stdout": "found 5 files",
        "stderr": "", "session_id": "", "log_file": "/tmp/log.json",
        "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
    }
    wf = _make_workflow()
    runner = WorkflowRunner(logs_dir=Path("/tmp/logs"))
    runner.run(wf)
    second_call_task = mock_exec.call_args_list[1][0][0]
    assert "found 5 files" in second_call_task.prompt
