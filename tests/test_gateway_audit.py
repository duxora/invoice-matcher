"""Tests for gateway audit logger."""
import json

from claude_scheduler.gateway.audit import AuditLogger


def test_audit_log_allow(tmp_path):
    log_file = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_file)
    logger.log("daily-review", "Read", "src/main.py", "medium", "allow")
    lines = log_file.read_text().strip().split("\n")
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["task"] == "daily-review"
    assert entry["tool"] == "Read"
    assert entry["decision"] == "allow"
    assert "ts" in entry


def test_audit_log_deny(tmp_path):
    log_file = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_file)
    logger.log("daily-review", "Read", ".env", "medium", "deny", reason="denied_pattern")
    entry = json.loads(log_file.read_text().strip())
    assert entry["decision"] == "deny"
    assert entry["reason"] == "denied_pattern"


def test_audit_query_by_task(tmp_path):
    log_file = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_file)
    logger.log("task-a", "Read", "a.py", "low", "allow")
    logger.log("task-b", "Read", "b.py", "low", "allow")
    logger.log("task-a", "Bash", "git status", "low", "deny")
    entries = logger.query(task="task-a")
    assert len(entries) == 2
