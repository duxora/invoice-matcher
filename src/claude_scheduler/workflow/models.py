"""Data models for workflow orchestration."""

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
