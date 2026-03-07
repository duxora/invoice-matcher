"""Policy engine for tool access control.

Parses TOML-based policies with tool/file/bash access control rules.
Each policy level (low/medium/high) maps to a set of permissions that
govern what tools can be used, which files can be accessed, and what
bash commands are allowed.
"""

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
        import tomli as tomllib  # type: ignore[no-redef]


@dataclass
class Policy:
    """A single security policy level with access control rules."""

    name: str
    allowed_tools: list[str] = field(default_factory=list)
    denied_patterns: list[str] = field(default_factory=list)
    bash_allowlist: list[str] = field(default_factory=list)
    require_approval: list[str] = field(default_factory=list)
    max_calls_per_minute: int = 60
    network_isolation: bool = False

    def is_tool_allowed(self, tool: str) -> bool:
        """Check whether a tool is permitted under this policy."""
        return tool in self.allowed_tools

    def is_file_allowed(self, file_path: str) -> bool:
        """Check whether a file path is permitted (not matching denied patterns)."""
        name = Path(file_path).name
        full = str(file_path)
        for pattern in self.denied_patterns:
            if fnmatch(name, pattern) or fnmatch(full, pattern):
                return False
        return True

    def needs_approval(self, tool: str) -> bool:
        """Check whether a tool requires explicit approval before use."""
        return tool in self.require_approval

    def is_bash_allowed(self, command: str) -> bool:
        """Check whether a bash command is permitted by the allowlist.

        If no allowlist is configured, all commands are allowed.
        Only the first token (the executable name) is checked.
        """
        if not self.bash_allowlist:
            return True
        cmd_name = command.strip().split()[0] if command.strip() else ""
        return cmd_name in self.bash_allowlist


def load_policies(path: Path) -> dict[str, Policy]:
    """Load policies from a TOML file.

    Expected format:
        [policy.low]
        allowed_tools = ["Read", "Grep"]
        ...
    """
    with open(path, "rb") as f:
        data = tomllib.load(f)

    policies: dict[str, Policy] = {}
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
