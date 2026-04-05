"""Tests for gateway middleware."""
from claude_scheduler.gateway.middleware import CheckResult, GatewayMiddleware
from claude_scheduler.gateway.policy import Policy


def _make_policy():
    return Policy(
        name="medium",
        allowed_tools=["Read", "Grep", "Glob", "Bash"],
        denied_patterns=["*.env", "*secret*"],
        bash_allowlist=["git", "ruff", "pytest"],
        require_approval=["Edit"],
        max_calls_per_minute=30,
    )


def test_middleware_allows_valid_call(tmp_path):
    mw = GatewayMiddleware(_make_policy(), audit_dir=tmp_path)
    result = mw.check("my-task", "Read", "src/main.py")
    assert result.allowed is True


def test_middleware_denies_disallowed_tool(tmp_path):
    mw = GatewayMiddleware(_make_policy(), audit_dir=tmp_path)
    result = mw.check("my-task", "Write", "src/main.py")
    assert result.allowed is False
    assert result.reason == "tool_not_allowed"


def test_middleware_denies_secret_file(tmp_path):
    mw = GatewayMiddleware(_make_policy(), audit_dir=tmp_path)
    result = mw.check("my-task", "Read", ".env")
    assert result.allowed is False
    assert result.reason == "denied_pattern"


def test_middleware_denies_bad_bash(tmp_path):
    mw = GatewayMiddleware(_make_policy(), audit_dir=tmp_path)
    result = mw.check("my-task", "Bash", "rm -rf /")
    assert result.allowed is False
    assert result.reason == "bash_not_allowlisted"


def test_middleware_flags_approval_needed(tmp_path):
    policy = _make_policy()
    policy.allowed_tools.append("Edit")
    mw = GatewayMiddleware(policy, audit_dir=tmp_path)
    result = mw.check("my-task", "Edit", "src/main.py")
    assert result.allowed is True
    assert result.needs_approval is True
