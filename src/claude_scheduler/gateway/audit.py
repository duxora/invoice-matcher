"""Structured audit logging for gateway decisions."""
import json
from datetime import datetime, timezone
from pathlib import Path


class AuditLogger:
    """Logs gateway tool-call decisions in JSONL format."""

    def __init__(self, log_file: Path):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log(self, task: str, tool: str, args: str, policy: str,
            decision: str, reason: str = "") -> None:
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
        """Query audit log entries with optional filters."""
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
