"""Parse .workflow markdown files into Workflow objects."""

import re
from pathlib import Path

from .models import Step, Workflow


def _extract_section(text: str, heading: str) -> str:
    """Extract content under a ## heading, up to the next ## or end of file."""
    pattern = rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)"
    m = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _parse_steps(text: str) -> list[Step]:
    """Parse numbered list items into Step objects."""
    steps = []
    for i, m in enumerate(
        re.finditer(r"^\d+\.\s+(.+)$", text, re.MULTILINE), start=1
    ):
        steps.append(Step(order=i, description=m.group(1).strip()))
    return steps


def _parse_security(text: str) -> dict:
    """Parse security section key-value pairs."""
    result: dict[str, str] = {}
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
    """Parse a .workflow markdown file into a Workflow object.

    Args:
        path: Path to the .workflow file.

    Returns:
        A Workflow instance populated from the file contents.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Workflow file not found: {path}")

    text = path.read_text()

    # Extract workflow name from top-level heading
    name_match = re.search(r"^# (.+)$", text, re.MULTILINE)
    name = name_match.group(1).strip() if name_match else path.stem

    # Extract trigger value
    trigger_text = _extract_section(text, "Trigger")
    trigger = ""
    for line in trigger_text.splitlines():
        if ":" in line:
            # Take everything after the first colon (e.g., "schedule: daily 09:00" -> "daily 09:00")
            trigger = line.split(":", 1)[1].strip()
            break
    if not trigger:
        trigger = trigger_text.strip()

    # Parse steps
    steps_text = _extract_section(text, "Steps")
    steps = _parse_steps(steps_text)

    # Parse on_failure
    failure_text = _extract_section(text, "On Failure")
    on_failure = failure_text.strip() if failure_text else "retry_once"

    # Parse security settings
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
    """Find and parse all .workflow files in a directory.

    Args:
        directory: Directory to search for .workflow files.

    Returns:
        List of parsed Workflow objects, sorted by filename.
    """
    directory = Path(directory)
    workflows = []
    for f in sorted(directory.glob("*.workflow")):
        try:
            workflows.append(parse_workflow(f))
        except (ValueError, FileNotFoundError):
            pass
    return workflows
