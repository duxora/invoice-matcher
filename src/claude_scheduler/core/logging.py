"""Structured logging for claude-scheduler."""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from claude_scheduler.config import get_config

_logger: logging.Logger | None = None

def get_logger() -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger

    cfg = get_config()
    cfg.paths.logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = cfg.paths.logs_dir / "scheduler.log"

    _logger = logging.getLogger("claude_scheduler")
    _logger.setLevel(logging.INFO)

    # File handler with rotation (5MB, keep 3 backups)
    fh = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    _logger.addHandler(fh)

    return _logger
