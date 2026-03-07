"""Gateway middleware -- checks tool calls against policy."""
from dataclasses import dataclass
from pathlib import Path

from .audit import AuditLogger
from .policy import Policy

# Tools that operate on file paths and should be checked against denied patterns.
_FILE_TOOLS = frozenset({"Read", "Write", "Edit", "Glob"})


@dataclass
class CheckResult:
    """Outcome of a middleware policy check."""

    allowed: bool
    reason: str = ""
    needs_approval: bool = False


class GatewayMiddleware:
    """Checks tool calls against a policy and logs decisions via audit logger."""

    def __init__(self, policy: Policy, audit_dir: Path) -> None:
        self.policy = policy
        self.audit = AuditLogger(audit_dir / "audit.jsonl")

    def check(self, task: str, tool: str, args: str = "") -> CheckResult:
        """Evaluate a tool call against the policy.

        Returns a CheckResult indicating whether the call is allowed,
        and if approval is needed before execution.
        """
        if not self.policy.is_tool_allowed(tool):
            self.audit.log(task, tool, args, self.policy.name, "deny", "tool_not_allowed")
            return CheckResult(allowed=False, reason="tool_not_allowed")

        if tool in _FILE_TOOLS and args:
            if not self.policy.is_file_allowed(args):
                self.audit.log(task, tool, args, self.policy.name, "deny", "denied_pattern")
                return CheckResult(allowed=False, reason="denied_pattern")

        if tool == "Bash" and args:
            if not self.policy.is_bash_allowed(args):
                self.audit.log(task, tool, args, self.policy.name, "deny", "bash_not_allowlisted")
                return CheckResult(allowed=False, reason="bash_not_allowlisted")

        needs_approval = self.policy.needs_approval(tool)
        self.audit.log(task, tool, args, self.policy.name, "allow")
        return CheckResult(allowed=True, needs_approval=needs_approval)
