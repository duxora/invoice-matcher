"""Terminal recording backends."""
import shutil
import subprocess
import platform
from pathlib import Path
from datetime import datetime


class RecordingBackend:
    """Base recording backend."""

    def start(self, output_path: Path) -> None:
        raise NotImplementedError

    def stop(self) -> Path:
        raise NotImplementedError


class AsciinemaBackend(RecordingBackend):
    """Record using asciinema (produces .cast files)."""

    def __init__(self):
        self.proc = None
        self.output_path = None

    @staticmethod
    def is_available() -> bool:
        return shutil.which("asciinema") is not None

    def start(self, output_path: Path) -> subprocess.Popen:
        self.output_path = output_path.with_suffix(".cast")
        self.proc = subprocess.Popen(
            [
                "asciinema", "rec", "--idle-time-limit", "2",
                "--title", output_path.stem, str(self.output_path),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return self.proc

    def stop(self) -> Path:
        if self.proc:
            self.proc.stdin.close()
            self.proc.wait(timeout=10)
        return self.output_path


class ScriptBackend(RecordingBackend):
    """Fallback: record using macOS/Linux `script` command (produces .txt files)."""

    def __init__(self):
        self.proc = None
        self.output_path = None

    @staticmethod
    def is_available() -> bool:
        return shutil.which("script") is not None

    def start(self, output_path: Path) -> subprocess.Popen:
        self.output_path = output_path.with_suffix(".txt")
        if platform.system() == "Darwin":
            cmd = ["script", "-q", str(self.output_path)]
        else:
            cmd = ["script", "-q", str(self.output_path)]
        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return self.proc

    def stop(self) -> Path:
        if self.proc:
            self.proc.stdin.write(b"exit\n")
            self.proc.stdin.close()
            self.proc.wait(timeout=10)
        return self.output_path


class ScreencaptureBackend:
    """macOS screen video recording."""

    def __init__(self):
        self.proc = None
        self.output_path = None

    @staticmethod
    def is_available() -> bool:
        return shutil.which("screencapture") is not None

    def start(self, output_path: Path) -> subprocess.Popen:
        self.output_path = output_path.with_suffix(".mov")
        self.proc = subprocess.Popen(
            ["screencapture", "-v", str(self.output_path)],
            stdin=subprocess.PIPE,
        )
        return self.proc

    def stop(self) -> Path:
        if self.proc:
            self.proc.terminate()
            self.proc.wait(timeout=10)
        return self.output_path


def get_best_backend() -> RecordingBackend:
    """Return the best available recording backend."""
    if AsciinemaBackend.is_available():
        return AsciinemaBackend()
    if ScriptBackend.is_available():
        return ScriptBackend()
    raise RuntimeError(
        "No recording backend available. Install asciinema: brew install asciinema"
    )


def get_output_dir() -> Path:
    """Get/create demo output directory."""
    output_dir = Path.home() / ".config" / "claude-scheduler" / "demos"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def generate_output_path(name: str) -> Path:
    """Generate timestamped output path."""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return get_output_dir() / f"demo-{name}-{ts}"


def convert_to_gif(cast_file: Path, output_gif: Path | None = None) -> Path | None:
    """Convert .cast to .gif using agg (asciinema gif generator)."""
    if not shutil.which("agg"):
        return None
    gif_path = output_gif or cast_file.with_suffix(".gif")
    result = subprocess.run(
        ["agg", str(cast_file), str(gif_path)],
        capture_output=True,
    )
    return gif_path if result.returncode == 0 else None
