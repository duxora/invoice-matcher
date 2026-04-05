"""Configuration loader for claude-scheduler."""
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

CONFIG_DIR = Path(os.environ.get(
    "CS_CONFIG_DIR",
    Path.home() / ".config" / "claude-scheduler"
))
CONFIG_FILE = CONFIG_DIR / "config.toml"

DEFAULT_CONFIG = """\
[server]
port = 7070
host = "127.0.0.1"

[paths]
tasks_dir = "~/.config/claude-scheduler/tasks"
logs_dir = "~/.config/claude-scheduler/logs"
data_dir = "~/.config/claude-scheduler/data"

[defaults]
model = "claude-sonnet-4-6"
tools = "Read,Grep,Glob"
max_turns = 10
timeout = 300
retry = 1
on_failure = "investigate"
"""


@dataclass
class ServerConfig:
    port: int = 7070
    host: str = "127.0.0.1"


@dataclass
class PathsConfig:
    tasks_dir: Path = field(default_factory=lambda: CONFIG_DIR / "tasks")
    logs_dir: Path = field(default_factory=lambda: CONFIG_DIR / "logs")
    data_dir: Path = field(default_factory=lambda: CONFIG_DIR / "data")


@dataclass
class DefaultsConfig:
    model: str = "claude-sonnet-4-6"
    tools: str = "Read,Grep,Glob"
    max_turns: int = 10
    timeout: int = 300
    retry: int = 1
    on_failure: str = "investigate"


@dataclass
class Config:
    server: ServerConfig = field(default_factory=ServerConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    defaults: DefaultsConfig = field(default_factory=DefaultsConfig)


def _resolve_path(p: str) -> Path:
    """Expand ~ and env vars in path strings."""
    return Path(os.path.expandvars(os.path.expanduser(p)))


def load_config() -> Config:
    """Load config from file, falling back to defaults."""
    cfg = Config()
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "rb") as f:
            data = tomllib.load(f)
        if "server" in data:
            cfg.server.port = data["server"].get("port", cfg.server.port)
            cfg.server.host = data["server"].get("host", cfg.server.host)
        if "paths" in data:
            if "tasks_dir" in data["paths"]:
                cfg.paths.tasks_dir = _resolve_path(data["paths"]["tasks_dir"])
            if "logs_dir" in data["paths"]:
                cfg.paths.logs_dir = _resolve_path(data["paths"]["logs_dir"])
            if "data_dir" in data["paths"]:
                cfg.paths.data_dir = _resolve_path(data["paths"]["data_dir"])
        if "defaults" in data:
            d = data["defaults"]
            cfg.defaults.model = d.get("model", cfg.defaults.model)
            cfg.defaults.tools = d.get("tools", cfg.defaults.tools)
            cfg.defaults.max_turns = d.get("max_turns", cfg.defaults.max_turns)
            cfg.defaults.timeout = d.get("timeout", cfg.defaults.timeout)
            cfg.defaults.retry = d.get("retry", cfg.defaults.retry)
            cfg.defaults.on_failure = d.get("on_failure", cfg.defaults.on_failure)
    return cfg


def init_config():
    """Create config directory and default config file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    cfg.paths.tasks_dir.mkdir(parents=True, exist_ok=True)
    cfg.paths.logs_dir.mkdir(parents=True, exist_ok=True)
    cfg.paths.data_dir.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(DEFAULT_CONFIG)
    return cfg


# Singleton for use across the app
_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = load_config()
    return _config
