"""Server configuration."""
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
SCHEDULER_DIR = Path.home() / ".config" / "claude-scheduler"
TASKS_DIR = SCHEDULER_DIR / "tasks"
LOGS_DIR = SCHEDULER_DIR / "logs"
DATA_DIR = SCHEDULER_DIR / "data"
APPS_DIR = ROOT / "apps"

DEFAULT_PORT = 7070
