"""Self-healing remediation agent — resumes failed sessions via claude --resume."""
import json
import subprocess
import os
from pathlib import Path
from .models import Task
from .executor import _extract_session_id

# Includes task name so callers can identify which task is being remediated
RESUME_PROMPT = """Task: {task_name} — FAILED and needs remediation.

Error: {error_message}
Stderr: {stderr_output}
This is attempt {attempt} of the task (consecutive failures: {consecutive_failures}).
{user_guidance_section}
Investigate the root cause and fix it if possible. If you need human help,
explain clearly what's needed.

IMPORTANT: Start your response with either:
- "FIXED:" followed by what you did to resolve the issue
- "NEEDS_USER:" followed by what the human needs to do
"""

FRESH_PROMPT = """A scheduled task has FAILED and needs investigation.

Task: {task_name} | Working Directory: {workdir}
Attempt: {attempt} | Consecutive Failures: {consecutive_failures}

Error: {error_message}
Stderr: {stderr_output}

Original task prompt: {original_prompt}
{user_guidance_section}
Investigate the root cause, fix it if possible, or explain what the human needs to do.
Start with "FIXED:" or "NEEDS_USER:".
"""

def build_remediation_prompt(
    task: Task,
    error_message: str,
    stderr_output: str = "",
    attempt: int = 1,
    consecutive_failures: int = 1,
    user_guidance: str = "",
    has_session: bool = True,
) -> str:
    guidance_section = ""
    if user_guidance:
        guidance_section = f"\nUser Guidance: {user_guidance}\n"

    if has_session:
        return RESUME_PROMPT.format(
            task_name=task.name,
            error_message=error_message,
            stderr_output=stderr_output or "(none)",
            attempt=attempt,
            consecutive_failures=consecutive_failures,
            user_guidance_section=guidance_section,
        )
    else:
        return FRESH_PROMPT.format(
            task_name=task.name,
            workdir=task.workdir or "not set",
            attempt=attempt,
            consecutive_failures=consecutive_failures,
            error_message=error_message,
            stderr_output=stderr_output or "(none)",
            original_prompt=task.prompt,
            user_guidance_section=guidance_section,
        )

def remediate_error(
    task: Task,
    error_message: str,
    stderr_output: str = "",
    attempt: int = 1,
    consecutive_failures: int = 1,
    user_guidance: str = "",
    session_id: str = "",
    logs_dir: Path | None = None,
) -> dict:
    has_session = bool(session_id)
    prompt = build_remediation_prompt(
        task=task,
        error_message=error_message,
        stderr_output=stderr_output,
        attempt=attempt,
        consecutive_failures=consecutive_failures,
        user_guidance=user_guidance,
        has_session=has_session,
    )

    tools = task.remediation_tools or task.tools
    max_turns = task.remediation_max_turns
    workdir = os.path.expanduser(task.workdir) if task.workdir else None

    cmd = [
        "claude", "-p", prompt,
        "--allowedTools", tools,
        "--max-turns", str(max_turns),
        "--model", task.model,
        "--output-format", "json",
    ]
    if session_id:
        cmd.extend(["--resume", session_id])

    try:
        proc = subprocess.run(
            cmd, capture_output=True, timeout=task.timeout * 2, cwd=workdir)

        output = proc.stdout.decode(errors="replace")
        stderr = proc.stderr.decode(errors="replace")
        rem_session_id = _extract_session_id(output)

        if logs_dir:
            logs_dir.mkdir(parents=True, exist_ok=True)
            (logs_dir / f"{task.slug}-remediation.json").write_text(output)

        success = proc.returncode == 0 and "FIXED:" in output.upper()
        needs_user = "NEEDS_USER:" in output.upper()

        return {
            "success": success,
            "needs_user": needs_user or (not success),
            "output": output,
            "stderr": stderr,
            "exit_code": proc.returncode,
            "session_id": rem_session_id,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "needs_user": True,
            "output": "Remediation agent timed out",
            "stderr": "",
            "exit_code": None,
            "session_id": "",
        }
