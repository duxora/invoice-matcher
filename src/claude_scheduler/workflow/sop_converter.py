"""Convert plain-English SOPs into .workflow files."""

import json
import subprocess
from pathlib import Path


CONVERT_PROMPT = """\
Convert this Standard Operating Procedure into a structured workflow.

SOP:
---
{sop_text}
---

Return ONLY JSON:
{{
  "name": "workflow name",
  "trigger": "schedule: daily HH:MM or every Nh",
  "steps": ["step 1 description", "step 2 description"],
  "security_level": "low|medium|high",
  "on_failure": "retry_once|notify|investigate"
}}
"""


def build_convert_prompt(sop_text: str) -> str:
    return CONVERT_PROMPT.format(sop_text=sop_text)


def parse_workflow_json(raw: str) -> dict:
    try:
        data = json.loads(raw)
        if "result" in data:
            return json.loads(data["result"])
        return data
    except (json.JSONDecodeError, TypeError):
        return {}


def generate_workflow_file(workflow_data: dict) -> str:
    name = workflow_data.get("name", "Untitled Workflow")
    trigger = workflow_data.get("trigger", "schedule: daily 09:00")
    steps = workflow_data.get("steps", [])
    security = workflow_data.get("security_level", "high")
    on_failure = workflow_data.get("on_failure", "retry_once")

    lines = [f"# {name}", "", "## Trigger", trigger, "", "## Steps"]
    for i, step in enumerate(steps, 1):
        lines.append(f"{i}. {step}")
    lines.extend(
        ["", "## On Failure", on_failure, "", "## Security",
         f"level: {security}", "allowed_tools: Read, Grep, Glob"]
    )
    return "\n".join(lines) + "\n"


def convert_sop(
    sop_path: Path,
    output_path: Path | None = None,
    model: str = "claude-sonnet-4-6",
) -> Path:
    sop_text = Path(sop_path).read_text()
    prompt = build_convert_prompt(sop_text)
    cmd = ["claude", "-p", prompt, "--model", model, "--output-format", "json"]

    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=120)
        stdout = proc.stdout.decode(errors="replace")
        workflow_data = parse_workflow_json(stdout)
    except Exception:
        workflow_data = {}

    if not workflow_data:
        raise ValueError("Failed to parse SOP into workflow")

    content = generate_workflow_file(workflow_data)

    if output_path is None:
        slug = workflow_data.get("name", "untitled").lower().replace(" ", "-")
        output_path = sop_path.parent / f"{slug}.workflow"

    Path(output_path).write_text(content)
    return output_path
