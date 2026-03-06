"""File-watch trigger support for tasks."""
# File-watch triggers are implemented via launchd WatchPaths
# This module provides utilities for parsing watch_paths config

import os
from pathlib import Path

def expand_watch_paths(watch_paths: str) -> list[str]:
    """Expand comma-separated watch paths, resolving ~ and env vars."""
    paths = []
    for p in watch_paths.split(","):
        p = p.strip()
        if p:
            paths.append(os.path.expanduser(p))
    return paths
