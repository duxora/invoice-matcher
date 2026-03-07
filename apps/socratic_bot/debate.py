"""Interactive debate session using Claude CLI."""
import json
import subprocess

from .modes import get_system_prompt


class DebateSession:
    def __init__(self, mode: str = "socratic", model: str = "claude-sonnet-4-6"):
        self.mode = mode
        self.model = model
        self.system_prompt = get_system_prompt(mode)
        self.session_id = ""
        self.turn_count = 0
        self.history: list[dict] = []

    def send(self, message: str) -> str:
        cmd = [
            "claude", "-p",
            f"{self.system_prompt}\n\nUser says: {message}",
            "--model", self.model,
            "--output-format", "json",
        ]
        if self.session_id:
            cmd.extend(["--resume", self.session_id])

        proc = subprocess.run(cmd, capture_output=True, timeout=120)
        stdout = proc.stdout.decode(errors="replace")

        try:
            data = json.loads(stdout)
            response = data.get("result", stdout)
            self.session_id = data.get("session_id", self.session_id)
        except json.JSONDecodeError:
            response = stdout

        self.turn_count += 1
        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": response})
        return response

    def summary(self) -> dict:
        return {
            "mode": self.mode,
            "turns": self.turn_count,
            "session_id": self.session_id,
        }
