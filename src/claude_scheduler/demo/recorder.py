"""Terminal recording backends."""
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime


def get_output_dir() -> Path:
    """Get/create demo output directory."""
    output_dir = Path.home() / ".config" / "claude-scheduler" / "demos"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def generate_output_path(name: str) -> Path:
    """Generate timestamped output path."""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return get_output_dir() / f"demo-{name}-{ts}"


def record_command(command: list[str], output_path: Path,
                   title: str = "") -> Path:
    """Record a command's terminal output using the best available backend.

    Uses `asciinema rec -c <cmd>` which properly captures the command's
    full terminal output including colors and formatting.
    Falls back to running the command directly if no recorder is available.
    """
    if shutil.which("asciinema"):
        cast_path = output_path.with_suffix(".cast")
        cmd = [
            "asciinema", "rec",
            "--idle-time-limit", "2",
            "--overwrite",
            "-c", " ".join(command),
        ]
        if title:
            cmd.extend(["--title", title])
        cmd.append(str(cast_path))
        subprocess.run(cmd, check=False)
        return cast_path
    else:
        # Fallback: just run the command, no recording
        subprocess.run(command, check=False)
        return output_path


def convert_to_gif(cast_file: Path, output_gif: Path | None = None) -> Path | None:
    """Convert .cast to .gif using agg (asciinema gif generator)."""
    if not shutil.which("agg"):
        return None
    gif_path = output_gif or cast_file.with_suffix(".gif")
    result = subprocess.run(
        ["agg", "--font-size", "14", str(cast_file), str(gif_path)],
        capture_output=True,
    )
    return gif_path if result.returncode == 0 else None


class AsciinemaBackend:
    """Check asciinema availability."""
    @staticmethod
    def is_available() -> bool:
        return shutil.which("asciinema") is not None


class ScriptBackend:
    """Check script availability."""
    @staticmethod
    def is_available() -> bool:
        return shutil.which("script") is not None
