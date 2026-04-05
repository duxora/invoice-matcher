"""Tests for workflow and gateway CLI subcommands."""
import subprocess
import sys


def test_workflow_run_help():
    result = subprocess.run(
        [sys.executable, "-m", "claude_scheduler.cli", "workflow", "run", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "workflow" in result.stdout.lower() or "dry-run" in result.stdout.lower()


def test_gateway_audit_help():
    result = subprocess.run(
        [sys.executable, "-m", "claude_scheduler.cli", "gateway", "audit", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0


def test_workflow_dry_run():
    result = subprocess.run(
        [sys.executable, "-m", "claude_scheduler.cli", "workflow", "run",
         "tests/fixtures/sample.workflow", "--dry-run"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "Daily Code Quality Check" in result.stdout


def test_gateway_policy_help():
    result = subprocess.run(
        [sys.executable, "-m", "claude_scheduler.cli", "gateway", "policy", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0


def test_workflow_list_help():
    result = subprocess.run(
        [sys.executable, "-m", "claude_scheduler.cli", "workflow", "list", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0


def test_workflow_from_sop_help():
    result = subprocess.run(
        [sys.executable, "-m", "claude_scheduler.cli", "workflow", "from-sop", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
