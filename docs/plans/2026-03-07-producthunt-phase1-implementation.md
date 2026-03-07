# Phase 1: Workflow Orchestrator + MCP Gateway — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build Claude-native workflow orchestrator (natural language `.workflow` files) and MCP zero-trust gateway (policy-based tool access control with audit logging).

**Architecture:** Extends existing `claude-scheduler` core. Workflow files compile down to Task sequences executed by existing Orchestrator. Gateway wraps executor with policy middleware.

**Tech Stack:** Python 3.12, dataclasses, tomllib, SQLite, existing claude-scheduler infrastructure

---

## Task 1: Workflow Models

**Files:**
- Create: `src/claude_scheduler/workflow/__init__.py`
- Create: `src/claude_scheduler/workflow/models.py`
- Test: `tests/test_workflow_models.py`

**Step 1: Write failing test**

```python
# tests/test_workflow_models.py
from claude_scheduler.workflow.models import Workflow, Step

def test_workflow_creation():
    steps = [
        Step(order=1, description="Pull latest changes", tools="Bash(git)"),
        Step(order=2, description="Run linting", tools="Bash(ruff)"),
    ]
    wf = Workflow(
        name="Daily Code Check",
        trigger="daily 09:00",
        steps=steps,
        security_level="medium",
    )
    assert wf.slug == "daily-code-check"
    assert len(wf.steps) == 2
    assert wf.steps[0].tools == "Bash(git)"

def test_step_to_task_prompt():
    step = Step(order=1, description="Check for TODO comments in Python files", tools="Read,Grep,Glob")
    prompt = step.to_prompt(context="Previous step found 3 modified files.")
    assert "Check for TODO comments" in prompt
    assert "Previous step found 3 modified files" in prompt

def test_workflow_defaults():
    wf = Workflow(name="Test", trigger="daily 09:00", steps=[])
    assert wf.security_level == "medium"
    assert wf.on_failure == "retry_once"
    assert wf.allowed_tools == "Read,Grep,Glob"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_workflow_models.py -v`
Expected: FAIL — ModuleNotFoundError

**Step 3: Write implementation**

```python
# src/claude_scheduler/workflow/__init__.py
# Workflow orchestrator — natural language workflow files.

# src/claude_scheduler/workflow/models.py
from dataclasses import dataclass, field

@dataclass
class Step:
    order: int
    description: str
    tools: str = "Read,Grep,Glob"
    timeout: int = 300
    max_turns: int = 10

    def to_prompt(self, context: str = "") -> str:
        parts = [f"Execute this step: {self.description}"]
        if context:
            parts.append(f"\nContext from previous step:\n{context}")
        parts.append("\nProvide a clear summary of what you did and any output.")
        return "\n".join(parts)

@dataclass
class Workflow:
    name: str
    trigger: str
    steps: list[Step] = field(default_factory=list)
    security_level: str = "medium"
    on_failure: str = "retry_once"
    allowed_tools: str = "Read,Grep,Glob"
    workdir: str = ""
    model: str = "claude-sonnet-4-6"
    budget_usd: float = 0.0

    @property
    def slug(self) -> str:
        return self.name.lower().replace(" ", "-").strip("-")
```

**Step 4: Run test**

Run: `python -m pytest tests/test_workflow_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/claude_scheduler/workflow/ tests/test_workflow_models.py
git commit -m "feat(workflow): add Workflow and Step models"
```

---

## Task 2: Workflow Parser

**Files:**
- Create: `src/claude_scheduler/workflow/parser.py`
- Test: `tests/test_workflow_parser.py`
- Create: `tests/fixtures/sample.workflow`

**Step 1: Create test fixture**

```markdown
# tests/fixtures/sample.workflow
# Daily Code Quality Check

## Trigger
schedule: daily 09:00

## Steps
1. Pull latest changes from main branch
2. Run ruff linting on all Python files
3. Check for TODO/FIXME comments added in last 24h
4. Summarize findings

## On Failure
retry_once

## Security
level: medium
allowed_tools: Read, Grep, Glob, Bash(git, ruff)
```

**Step 2: Write failing test**

```python
# tests/test_workflow_parser.py
from pathlib import Path
from claude_scheduler.workflow.parser import parse_workflow, find_workflows

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
    """Workflow with only name, trigger, and steps."""
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
    (tmp_path / "a.workflow").write_text("# A\n\n## Trigger\nschedule: daily 09:00\n\n## Steps\n1. Do A\n")
    (tmp_path / "b.workflow").write_text("# B\n\n## Trigger\nschedule: daily 10:00\n\n## Steps\n1. Do B\n")
    (tmp_path / "not-a-workflow.txt").write_text("ignore me")
    workflows = find_workflows(tmp_path)
    assert len(workflows) == 2
```

**Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_workflow_parser.py -v`
Expected: FAIL

**Step 4: Write implementation**

```python
# src/claude_scheduler/workflow/parser.py
"""Parse .workflow markdown files into Workflow objects."""
import re
from pathlib import Path
from .models import Workflow, Step

def _extract_section(text: str, heading: str) -> str:
    pattern = rf'^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)'
    m = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else ""

def _parse_steps(text: str) -> list[Step]:
    steps = []
    for i, m in enumerate(re.finditer(r'^\d+\.\s+(.+)$', text, re.MULTILINE), start=1):
        steps.append(Step(order=i, description=m.group(1).strip()))
    return steps

def _parse_security(text: str) -> dict:
    result = {}
    for line in text.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip().lower()
            val = val.strip()
            if key == "level":
                result["security_level"] = val
            elif key == "allowed_tools":
                result["allowed_tools"] = val
    return result

def parse_workflow(path: Path) -> Workflow:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Workflow file not found: {path}")

    text = path.read_text()

    # Extract name from first heading
    name_match = re.search(r'^# (.+)$', text, re.MULTILINE)
    name = name_match.group(1).strip() if name_match else path.stem

    # Extract trigger
    trigger_text = _extract_section(text, "Trigger")
    trigger = ""
    for line in trigger_text.splitlines():
        if ":" in line:
            trigger = line.split(":", 1)[1].strip()
            break
    if not trigger:
        trigger = trigger_text.strip()

    # Extract steps
    steps_text = _extract_section(text, "Steps")
    steps = _parse_steps(steps_text)

    # Extract on_failure
    failure_text = _extract_section(text, "On Failure")
    on_failure = failure_text.strip() if failure_text else "retry_once"

    # Extract security
    security_text = _extract_section(text, "Security")
    security = _parse_security(security_text)

    return Workflow(
        name=name,
        trigger=trigger,
        steps=steps,
        on_failure=on_failure,
        **security,
    )

def find_workflows(directory: Path) -> list[Workflow]:
    directory = Path(directory)
    workflows = []
    for f in sorted(directory.glob("*.workflow")):
        try:
            workflows.append(parse_workflow(f))
        except (ValueError, FileNotFoundError):
            pass
    return workflows
```

**Step 5: Run tests**

Run: `python -m pytest tests/test_workflow_parser.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/claude_scheduler/workflow/parser.py tests/test_workflow_parser.py tests/fixtures/sample.workflow
git commit -m "feat(workflow): add workflow parser for .workflow markdown files"
```

---

## Task 3: Workflow Runner

**Files:**
- Create: `src/claude_scheduler/workflow/runner.py`
- Test: `tests/test_workflow_runner.py`

**Step 1: Write failing test**

```python
# tests/test_workflow_runner.py
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
    assert mock_exec.call_count == 1  # stopped after first failure

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
    # Second call should have context from first step
    second_call_task = mock_exec.call_args_list[1][0][0]
    assert "found 5 files" in second_call_task.prompt
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_workflow_runner.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/claude_scheduler/workflow/runner.py
"""Execute workflows as step pipelines."""
from pathlib import Path
from claude_scheduler.core.models import Task
from claude_scheduler.core.executor import execute_task
from .models import Workflow

class WorkflowRunner:
    def __init__(self, logs_dir: Path):
        self.logs_dir = logs_dir

    def _step_to_task(self, workflow: Workflow, step, context: str = "") -> Task:
        prompt = step.to_prompt(context=context)
        return Task(
            name=f"{workflow.slug}--step-{step.order}",
            schedule=workflow.trigger,
            prompt=prompt,
            file_path=Path(f"<workflow:{workflow.slug}>"),
            workdir=workflow.workdir,
            tools=step.tools or workflow.allowed_tools,
            max_turns=step.max_turns,
            model=workflow.model,
            timeout=step.timeout,
            security_level=workflow.security_level,
        )

    def run(self, workflow: Workflow) -> dict:
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        step_results = []
        context = ""

        for step in workflow.steps:
            task = self._step_to_task(workflow, step, context=context)
            result = execute_task(task, self.logs_dir)
            step_results.append({
                "step": step.order,
                "description": step.description,
                **result,
            })

            if result["status"] != "success":
                return {
                    "status": "failed",
                    "failed_step": step.order,
                    "step_results": step_results,
                }

            context = result.get("stdout", "")

        return {
            "status": "success",
            "step_results": step_results,
        }
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_workflow_runner.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/claude_scheduler/workflow/runner.py tests/test_workflow_runner.py
git commit -m "feat(workflow): add WorkflowRunner with step pipeline execution"
```

---

## Task 4: Gateway Policy Engine

**Files:**
- Create: `src/claude_scheduler/gateway/__init__.py`
- Create: `src/claude_scheduler/gateway/policy.py`
- Test: `tests/test_gateway_policy.py`

**Step 1: Write failing test**

```python
# tests/test_gateway_policy.py
import tempfile
from pathlib import Path
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
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gateway_policy.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/claude_scheduler/gateway/__init__.py
# MCP zero-trust gateway — policy-based tool access control.

# src/claude_scheduler/gateway/policy.py
"""Policy engine for tool access control."""
import sys
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

@dataclass
class Policy:
    name: str
    allowed_tools: list[str] = field(default_factory=list)
    denied_patterns: list[str] = field(default_factory=list)
    bash_allowlist: list[str] = field(default_factory=list)
    require_approval: list[str] = field(default_factory=list)
    max_calls_per_minute: int = 60
    network_isolation: bool = False

    def is_tool_allowed(self, tool: str) -> bool:
        return tool in self.allowed_tools

    def is_file_allowed(self, file_path: str) -> bool:
        name = Path(file_path).name
        full = str(file_path)
        for pattern in self.denied_patterns:
            if fnmatch(name, pattern) or fnmatch(full, pattern):
                return False
        return True

    def needs_approval(self, tool: str) -> bool:
        return tool in self.require_approval

    def is_bash_allowed(self, command: str) -> bool:
        if not self.bash_allowlist:
            return True
        cmd_name = command.strip().split()[0] if command.strip() else ""
        return cmd_name in self.bash_allowlist

def load_policies(path: Path) -> dict[str, Policy]:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    policies = {}
    for level, cfg in data.get("policy", {}).items():
        policies[level] = Policy(
            name=level,
            allowed_tools=cfg.get("allowed_tools", []),
            denied_patterns=cfg.get("denied_patterns", []),
            bash_allowlist=cfg.get("bash_allowlist", []),
            require_approval=cfg.get("require_approval", []),
            max_calls_per_minute=cfg.get("max_calls_per_minute", 60),
            network_isolation=cfg.get("network_isolation", False),
        )
    return policies
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_gateway_policy.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/claude_scheduler/gateway/ tests/test_gateway_policy.py
git commit -m "feat(gateway): add policy engine with tool/file/bash access control"
```

---

## Task 5: Gateway Audit Logger

**Files:**
- Create: `src/claude_scheduler/gateway/audit.py`
- Test: `tests/test_gateway_audit.py`

**Step 1: Write failing test**

```python
# tests/test_gateway_audit.py
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
```

**Step 2: Run test, verify fails**

Run: `python -m pytest tests/test_gateway_audit.py -v`

**Step 3: Write implementation**

```python
# src/claude_scheduler/gateway/audit.py
"""Structured audit logging for gateway decisions."""
import json
from datetime import datetime, timezone
from pathlib import Path

class AuditLogger:
    def __init__(self, log_file: Path):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log(self, task: str, tool: str, args: str, policy: str,
            decision: str, reason: str = ""):
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "task": task,
            "tool": tool,
            "args": args,
            "policy": policy,
            "decision": decision,
        }
        if reason:
            entry["reason"] = reason
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def query(self, task: str = "", since: str = "") -> list[dict]:
        if not self.log_file.exists():
            return []
        entries = []
        for line in self.log_file.read_text().strip().split("\n"):
            if not line:
                continue
            entry = json.loads(line)
            if task and entry.get("task") != task:
                continue
            if since and entry.get("ts", "") < since:
                continue
            entries.append(entry)
        return entries
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_gateway_audit.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/claude_scheduler/gateway/audit.py tests/test_gateway_audit.py
git commit -m "feat(gateway): add structured audit logger"
```

---

## Task 6: Gateway Middleware

**Files:**
- Create: `src/claude_scheduler/gateway/middleware.py`
- Test: `tests/test_gateway_middleware.py`

**Step 1: Write failing test**

```python
# tests/test_gateway_middleware.py
from claude_scheduler.gateway.policy import Policy
from claude_scheduler.gateway.middleware import GatewayMiddleware

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
```

**Step 2: Run test, verify fails**

Run: `python -m pytest tests/test_gateway_middleware.py -v`

**Step 3: Write implementation**

```python
# src/claude_scheduler/gateway/middleware.py
"""Gateway middleware — checks tool calls against policy."""
from dataclasses import dataclass
from pathlib import Path
from .policy import Policy
from .audit import AuditLogger

@dataclass
class CheckResult:
    allowed: bool
    reason: str = ""
    needs_approval: bool = False

class GatewayMiddleware:
    def __init__(self, policy: Policy, audit_dir: Path):
        self.policy = policy
        self.audit = AuditLogger(audit_dir / "audit.jsonl")

    def check(self, task: str, tool: str, args: str = "") -> CheckResult:
        # Check tool allowed
        if not self.policy.is_tool_allowed(tool):
            self.audit.log(task, tool, args, self.policy.name, "deny", "tool_not_allowed")
            return CheckResult(allowed=False, reason="tool_not_allowed")

        # Check file patterns for file-accessing tools
        if tool in ("Read", "Write", "Edit", "Glob") and args:
            if not self.policy.is_file_allowed(args):
                self.audit.log(task, tool, args, self.policy.name, "deny", "denied_pattern")
                return CheckResult(allowed=False, reason="denied_pattern")

        # Check bash allowlist
        if tool == "Bash" and args:
            if not self.policy.is_bash_allowed(args):
                self.audit.log(task, tool, args, self.policy.name, "deny", "bash_not_allowlisted")
                return CheckResult(allowed=False, reason="bash_not_allowlisted")

        # Check approval requirement
        needs_approval = self.policy.needs_approval(tool)
        self.audit.log(task, tool, args, self.policy.name, "allow")
        return CheckResult(allowed=True, needs_approval=needs_approval)
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_gateway_middleware.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/claude_scheduler/gateway/middleware.py tests/test_gateway_middleware.py
git commit -m "feat(gateway): add middleware with policy checking and audit"
```

---

## Task 7: CLI Commands for Workflow + Gateway

**Files:**
- Modify: `src/claude_scheduler/cli.py`
- Test: `tests/test_cli_workflow.py`

**Step 1: Write failing test**

```python
# tests/test_cli_workflow.py
import subprocess
import sys

def test_workflow_run_help():
    result = subprocess.run(
        [sys.executable, "-m", "claude_scheduler.cli", "workflow", "run", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "workflow" in result.stdout.lower()

def test_gateway_audit_help():
    result = subprocess.run(
        [sys.executable, "-m", "claude_scheduler.cli", "gateway", "audit", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
```

**Step 2: Run test, verify fails**

Run: `python -m pytest tests/test_cli_workflow.py -v`

**Step 3: Add CLI commands to `cli.py`**

Add these functions and subparsers to `src/claude_scheduler/cli.py`:

```python
# Add after existing cmd_ functions:

def cmd_workflow_run(args):
    from claude_scheduler.workflow.parser import parse_workflow
    from claude_scheduler.workflow.runner import WorkflowRunner
    cfg = get_config()
    wf = parse_workflow(Path(args.workflow_file))
    if args.dry_run:
        t = Table(show_header=False, box=None)
        t.add_row("[bold]Workflow[/bold]", wf.name)
        t.add_row("[bold]Trigger[/bold]", wf.trigger)
        t.add_row("[bold]Steps[/bold]", str(len(wf.steps)))
        t.add_row("[bold]Security[/bold]", wf.security_level)
        for s in wf.steps:
            t.add_row(f"  Step {s.order}", s.description)
        console.print(t)
        return
    runner = WorkflowRunner(logs_dir=cfg.paths.logs_dir)
    result = runner.run(wf)
    if result["status"] == "success":
        console.print(f"[green]Workflow '{wf.name}' completed successfully[/green]")
    else:
        console.print(f"[red]Workflow '{wf.name}' failed at step {result.get('failed_step')}[/red]")

def cmd_workflow_list(args):
    from claude_scheduler.workflow.parser import find_workflows
    cfg = get_config()
    workflows_dir = cfg.paths.tasks_dir
    workflows = find_workflows(workflows_dir)
    if not workflows:
        console.print("[dim]No workflows found.[/dim]")
        return
    t = Table(title="Workflows")
    t.add_column("Name")
    t.add_column("Trigger")
    t.add_column("Steps")
    t.add_column("Security")
    for wf in workflows:
        t.add_row(wf.name, wf.trigger, str(len(wf.steps)), wf.security_level)
    console.print(t)

def cmd_workflow_from_sop(args):
    console.print("[yellow]SOP converter will be implemented in Phase 5[/yellow]")

def cmd_gateway_audit(args):
    from claude_scheduler.gateway.audit import AuditLogger
    cfg = get_config()
    logger = AuditLogger(cfg.paths.data_dir / "audit.jsonl")
    entries = logger.query(task=args.task or "")
    if not entries:
        console.print("[dim]No audit entries found.[/dim]")
        return
    t = Table(title="Audit Log")
    t.add_column("Time")
    t.add_column("Task")
    t.add_column("Tool")
    t.add_column("Args", max_width=40)
    t.add_column("Decision")
    t.add_column("Reason")
    for e in entries[-50:]:
        style = "green" if e["decision"] == "allow" else "red"
        t.add_row(
            e["ts"][:19], e["task"], e["tool"],
            e.get("args", "")[:40], f"[{style}]{e['decision']}[/{style}]",
            e.get("reason", ""),
        )
    console.print(t)

def cmd_gateway_policy_list(args):
    from claude_scheduler.gateway.policy import load_policies
    cfg = get_config()
    policy_file = cfg.paths.tasks_dir.parent / "policies" / "default.toml"
    if not policy_file.exists():
        console.print(f"[dim]No policy file at {policy_file}[/dim]")
        return
    policies = load_policies(policy_file)
    for name, p in policies.items():
        console.print(Panel(
            f"Tools: {', '.join(p.allowed_tools)}\n"
            f"Denied: {', '.join(p.denied_patterns)}\n"
            f"Bash: {', '.join(p.bash_allowlist) or 'any'}\n"
            f"Approval: {', '.join(p.require_approval) or 'none'}\n"
            f"Rate: {p.max_calls_per_minute}/min\n"
            f"Network isolation: {p.network_isolation}",
            title=f"Policy: {name}",
        ))
```

Add to the argparse section in `main()`:

```python
    # workflow
    wf_parser = sub.add_parser("workflow", help="Workflow management")
    wf_sub = wf_parser.add_subparsers(dest="wf_command", required=True)

    p = wf_sub.add_parser("run", help="Run a workflow")
    p.add_argument("workflow_file")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_workflow_run)

    p = wf_sub.add_parser("list", help="List workflows")
    p.set_defaults(func=cmd_workflow_list)

    p = wf_sub.add_parser("from-sop", help="Convert SOP to workflow")
    p.add_argument("sop_file")
    p.set_defaults(func=cmd_workflow_from_sop)

    # gateway
    gw_parser = sub.add_parser("gateway", help="Security gateway")
    gw_sub = gw_parser.add_subparsers(dest="gw_command", required=True)

    p = gw_sub.add_parser("audit", help="View audit log")
    p.add_argument("--task", "-t")
    p.set_defaults(func=cmd_gateway_audit)

    p = gw_sub.add_parser("policy", help="List policies")
    p.set_defaults(func=cmd_gateway_policy_list)
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_cli_workflow.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/claude_scheduler/cli.py tests/test_cli_workflow.py
git commit -m "feat(cli): add workflow and gateway subcommands"
```

---

## Task 8: Default Policy File + Integration Test

**Files:**
- Create: `examples/policies/default.toml`
- Create: `examples/workflows/daily-code-check.workflow`
- Test: `tests/test_phase1_integration.py`

**Step 1: Create example files**

```toml
# examples/policies/default.toml
[policy.low]
allowed_tools = ["Read", "Grep", "Glob"]
denied_patterns = ["*.env", "*secret*", "*credentials*", "*password*"]
max_calls_per_minute = 60

[policy.medium]
allowed_tools = ["Read", "Grep", "Glob", "Bash", "Edit"]
bash_allowlist = ["git", "ruff", "pytest", "python"]
denied_patterns = ["*.env", "*secret*"]
require_approval = ["Edit"]
max_calls_per_minute = 30

[policy.high]
allowed_tools = ["Read", "Grep", "Glob", "Bash", "Edit", "Write"]
bash_allowlist = ["git", "ruff", "pytest", "python", "pip"]
require_approval = ["Bash", "Edit", "Write"]
network_isolation = true
max_calls_per_minute = 10
```

```markdown
# examples/workflows/daily-code-check.workflow
# Daily Code Quality Check

## Trigger
schedule: daily 09:00

## Steps
1. Pull latest changes from main branch
2. Run ruff linting on all Python files
3. Check for TODO/FIXME comments added in last 24h
4. Summarize findings

## On Failure
retry_once

## Security
level: medium
allowed_tools: Read, Grep, Glob, Bash(git, ruff)
```

**Step 2: Write integration test**

```python
# tests/test_phase1_integration.py
from pathlib import Path
from claude_scheduler.workflow.parser import parse_workflow
from claude_scheduler.workflow.models import Workflow
from claude_scheduler.gateway.policy import load_policies
from claude_scheduler.gateway.middleware import GatewayMiddleware

EXAMPLES = Path(__file__).parent.parent / "examples"

def test_parse_example_workflow():
    wf = parse_workflow(EXAMPLES / "workflows" / "daily-code-check.workflow")
    assert wf.name == "Daily Code Quality Check"
    assert len(wf.steps) == 4

def test_load_example_policies():
    policies = load_policies(EXAMPLES / "policies" / "default.toml")
    assert len(policies) == 3
    assert policies["high"].network_isolation is True

def test_workflow_with_gateway(tmp_path):
    wf = parse_workflow(EXAMPLES / "workflows" / "daily-code-check.workflow")
    policies = load_policies(EXAMPLES / "policies" / "default.toml")
    mw = GatewayMiddleware(policies[wf.security_level], audit_dir=tmp_path)

    # Step tools should be allowed
    assert mw.check("test", "Read", "src/main.py").allowed is True
    assert mw.check("test", "Grep", "TODO").allowed is True

    # Secrets should be denied
    assert mw.check("test", "Read", ".env").allowed is False

    # Dangerous bash should be denied
    assert mw.check("test", "Bash", "rm -rf /").allowed is False
```

**Step 3: Run integration test**

Run: `python -m pytest tests/test_phase1_integration.py -v`
Expected: PASS

**Step 4: Commit**

```bash
git add examples/ tests/test_phase1_integration.py
git commit -m "feat: add example workflow/policy files and integration tests"
```
