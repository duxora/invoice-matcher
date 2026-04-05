"""Scripted demo sequences for each tool."""
import time
import sys


def _type_slow(text: str, delay: float = 0.04):
    """Simulate typing for demo effect."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _pause(seconds: float = 1.0):
    time.sleep(seconds)


def _header(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")
    _pause(1.5)


DEMO_SCRIPTS = {
    "workflow": {
        "name": "Workflow Orchestrator",
        "description": "Define and run workflows in natural language",
        "steps": [
            ("header", "Demo: Workflow Orchestrator"),
            ("type", "# Let's look at a workflow file"),
            ("pause", 1),
            ("cmd", "cat examples/workflows/daily-code-check.workflow"),
            ("pause", 2),
            ("type", "# Now let's dry-run it"),
            ("pause", 0.5),
            ("cmd", "python -m claude_scheduler.cli workflow run examples/workflows/daily-code-check.workflow --dry-run"),
            ("pause", 2),
            ("type", "# List all available workflows"),
            ("cmd", "python -m claude_scheduler.cli workflow list"),
            ("pause", 2),
        ],
    },
    "gateway": {
        "name": "Security Gateway",
        "description": "Zero-trust tool access control",
        "steps": [
            ("header", "Demo: MCP Security Gateway"),
            ("type", "# View security policies"),
            ("pause", 0.5),
            ("cmd", "cat examples/policies/default.toml"),
            ("pause", 2),
            ("type", "# The gateway enforces these policies on every tool call"),
            ("type", "# Let's see the audit log"),
            ("cmd", "python -m claude_scheduler.cli gateway audit"),
            ("pause", 2),
        ],
    },
    "debate": {
        "name": "Socratic Debate Bot",
        "description": "Critical thinking practice",
        "steps": [
            ("header", "Demo: Socratic Debate Bot"),
            ("type", "# Available modes: socratic, devil, steelman"),
            ("pause", 1),
            ("cmd", "python -m claude_scheduler.cli debate --help"),
            ("pause", 2),
            ("type", "# The debate bot challenges your reasoning"),
            ("type", "# Example: cs debate --mode devil --topic 'AI will replace developers'"),
            ("pause", 2),
        ],
    },
    "journal": {
        "name": "Daily Journal",
        "description": "English + critical thinking practice",
        "steps": [
            ("header", "Demo: Daily Reflection Journal"),
            ("type", "# Check your journal stats"),
            ("cmd", "python -m claude_scheduler.cli journal stats"),
            ("pause", 2),
            ("type", "# Check your writing streak"),
            ("cmd", "python -m claude_scheduler.cli journal streak"),
            ("pause", 2),
            ("type", "# Start writing: cs journal"),
            ("type", "# You get a daily prompt, write in your editor, get AI feedback"),
            ("pause", 2),
        ],
    },
    "speak": {
        "name": "Speaking Coach",
        "description": "English speaking practice",
        "steps": [
            ("header", "Demo: English Speaking Coach"),
            ("type", "# Available scenarios:"),
            ("type", "#   standup, code_review, presentation, interview, free"),
            ("pause", 1),
            ("cmd", "python -m claude_scheduler.cli speak --help"),
            ("pause", 2),
            ("type", "# Check your progress"),
            ("cmd", "python -m claude_scheduler.cli speak progress"),
            ("pause", 2),
        ],
    },
    "kb": {
        "name": "Knowledge Base",
        "description": "Obsidian AI bridge",
        "steps": [
            ("header", "Demo: Knowledge Base (Obsidian Bridge)"),
            ("type", "# Index your Obsidian vault"),
            ("type", "# cs kb reindex --vault ~/Documents/Obsidian"),
            ("pause", 1),
            ("type", "# Search your notes"),
            ("type", "# cs kb search 'python patterns'"),
            ("pause", 1),
            ("type", "# Ask questions across all your notes"),
            ("type", "# cs kb ask 'What design patterns should I use?'"),
            ("pause", 2),
        ],
    },
}


def get_demo_script(name: str) -> dict:
    """Get a demo script by name."""
    if name not in DEMO_SCRIPTS:
        raise ValueError(
            f"Unknown demo: {name}. Available: {', '.join(DEMO_SCRIPTS)}"
        )
    return DEMO_SCRIPTS[name]


def list_demos() -> list[dict]:
    """List all available demos."""
    return [
        {"key": k, "name": v["name"], "description": v["description"]}
        for k, v in DEMO_SCRIPTS.items()
    ]
