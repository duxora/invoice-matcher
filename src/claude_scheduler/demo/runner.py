"""Execute demo scripts with optional recording."""
import os
import subprocess
from pathlib import Path

from .scripts import get_demo_script, DEMO_SCRIPTS, _type_slow, _pause, _header
from .recorder import get_best_backend, generate_output_path, convert_to_gif


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


def run_demo(
    name: str,
    record: bool = True,
    workdir: str = "",
    to_gif: bool = False,
) -> Path | None:
    """Run a demo script, optionally recording it."""
    script = get_demo_script(name)
    output_path = None
    backend = None

    if record:
        try:
            backend = get_best_backend()
            output_path_base = generate_output_path(name)
            backend.start(output_path_base)
        except RuntimeError:
            record = False

    # Run all steps
    for step in script["steps"]:
        _run_step(step, workdir=workdir)

    if record and backend:
        output_path = backend.stop()
        if to_gif and output_path and output_path.suffix == ".cast":
            gif_path = convert_to_gif(output_path)
            if gif_path:
                return gif_path
        return output_path

    return None


def run_all_demos(
    record: bool = True,
    workdir: str = "",
    to_gif: bool = False,
) -> list[Path]:
    """Run all demo scripts."""
    results = []
    for name in DEMO_SCRIPTS:
        _header(f"=== {DEMO_SCRIPTS[name]['name']} ===")
        path = run_demo(name, record=record, workdir=workdir, to_gif=to_gif)
        if path:
            results.append(path)
        _pause(1)
    return results
