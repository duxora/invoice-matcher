"""Tests for gateway policy engine — tool/file/bash access control."""

from claude_scheduler.gateway.policy import Policy, load_policies

SAMPLE_POLICY = """\
[policy.low]
allowed_tools = ["Read", "Grep", "Glob"]
denied_patterns = ["*.env", "*secret*"]
max_calls_per_minute = 60

[policy.medium]
allowed_tools = ["Read", "Grep", "Glob", "Bash", "Edit"]
bash_allowlist = ["git", "ruff", "pytest"]
denied_patterns = ["*.env", "*secret*"]
require_approval = ["Edit"]
max_calls_per_minute = 30

[policy.high]
allowed_tools = ["Read", "Grep", "Glob", "Bash", "Edit", "Write"]
bash_allowlist = ["git", "ruff", "pytest", "python", "pip"]
require_approval = ["Bash", "Edit", "Write"]
network_isolation = true
max_calls_per_minute = 10
"""


def _write_policy(tmp_path):
    p = tmp_path / "policy.toml"
    p.write_text(SAMPLE_POLICY)
    return p


def test_load_policies(tmp_path):
    path = _write_policy(tmp_path)
    policies = load_policies(path)
    assert "low" in policies
    assert "medium" in policies
    assert "high" in policies


def test_policy_allows_tool(tmp_path):
    path = _write_policy(tmp_path)
    policies = load_policies(path)
    p = policies["low"]
    assert p.is_tool_allowed("Read") is True
    assert p.is_tool_allowed("Bash") is False


def test_policy_denies_file_pattern(tmp_path):
    path = _write_policy(tmp_path)
    policies = load_policies(path)
    p = policies["medium"]
    assert p.is_file_allowed("src/main.py") is True
    assert p.is_file_allowed(".env") is False
    assert p.is_file_allowed("config/secret_key.txt") is False


def test_policy_requires_approval(tmp_path):
    path = _write_policy(tmp_path)
    policies = load_policies(path)
    p = policies["medium"]
    assert p.needs_approval("Edit") is True
    assert p.needs_approval("Read") is False


def test_policy_bash_allowlist(tmp_path):
    path = _write_policy(tmp_path)
    policies = load_policies(path)
    p = policies["medium"]
    assert p.is_bash_allowed("git status") is True
    assert p.is_bash_allowed("rm -rf /") is False


def test_low_policy_has_no_bash_allowlist(tmp_path):
    """Low policy has no bash_allowlist and no Bash in allowed_tools."""
    path = _write_policy(tmp_path)
    policies = load_policies(path)
    p = policies["low"]
    assert p.bash_allowlist == []


def test_high_policy_network_isolation(tmp_path):
    path = _write_policy(tmp_path)
    policies = load_policies(path)
    p = policies["high"]
    assert p.network_isolation is True
    assert policies["low"].network_isolation is False


def test_high_policy_max_calls(tmp_path):
    path = _write_policy(tmp_path)
    policies = load_policies(path)
    assert policies["high"].max_calls_per_minute == 10
    assert policies["low"].max_calls_per_minute == 60
