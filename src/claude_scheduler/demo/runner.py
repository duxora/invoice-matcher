"""Execute demo scripts with optional recording."""
import os
import subprocess
import sys
from pathlib import Path

from .scripts import get_demo_script, DEMO_SCRIPTS, _type_slow, _pause, _header
from .recorder import record_command, generate_output_path, convert_to_gif


def _run_step(step: tuple, workdir: str = ""):
    """Execute a single demo step."""
    action = step[0]
    if action == "header":
        _header(step[1])
    elif action == "type":
        _type_slow(step[1])
    elif action == "pause":
        _pause(step[1])
    elif action == "cmd":
        print(f"$ {step[1]}")
        _pause(0.3)
        subprocess.run(
            step[1],
            shell=True,
            cwd=workdir or None,
            env={**os.environ, "TERM": "xterm-256color"},
        )
        _pause(0.5)


def _run_steps(name: str, workdir: str = ""):
    """Run all steps for a named demo."""
    script = get_demo_script(name)
    for step in script["steps"]:
        _run_step(step, workdir=workdir)


def run_demo(
    name: str,
    record: bool = True,
    workdir: str = "",
    to_gif: bool = False,
) -> Path | None:
    """Run a demo script, optionally recording it via asciinema rec -c.

    The key insight: asciinema rec -c <command> runs the command inside
    a recorded pseudo-terminal. So we invoke ourselves as the command.
    """
    if not record:
        _run_steps(name, workdir=workdir)
        return None

    output_path = generate_output_path(name)

    # Build a command that re-invokes this module to run the demo steps
    # without recording (asciinema handles the recording)
    demo_cmd = [
        sys.executable, "-m", "claude_scheduler.demo.runner",
        "--run", name,
    ]
    if workdir:
        demo_cmd.extend(["--workdir", workdir])

    cast_path = record_command(
        command=demo_cmd,
        output_path=output_path,
        title=get_demo_script(name)["name"],
    )

    if to_gif and cast_path and cast_path.suffix == ".cast":
        gif_path = convert_to_gif(cast_path)
        if gif_path:
            return gif_path

    return cast_path


def run_all_demos(
    record: bool = True,
    workdir: str = "",
    to_gif: bool = False,
) -> list[Path]:
    """Run all demo scripts."""
    results = []
    for name in DEMO_SCRIPTS:
        path = run_demo(name, record=record, workdir=workdir, to_gif=to_gif)
        if path:
            results.append(path)
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, help="Demo name to run")
    parser.add_argument("--workdir", default="", help="Working directory")
    args = parser.parse_args()
    _run_steps(args.run, workdir=args.workdir)
