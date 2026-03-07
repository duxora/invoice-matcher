"""Shared test fixtures and configuration."""
import json
import shutil
from pathlib import Path

import pytest

OUTPUT_DIR = Path(__file__).parent / "output"


def pytest_addoption(parser):
    parser.addoption(
        "--save-output",
        action="store_true",
        default=False,
        help="Save test output files to tests/output/ for inspection",
    )


@pytest.fixture
def save_output(request):
    """Fixture that provides a per-test output directory.

    Usage in tests:
        def test_something(save_output):
            # do work that produces files in some_dir...
            save_output(some_dir)             # copy a directory
            save_output(some_dir, "renamed")  # copy with custom name
            save_output(data, "result.json")  # save dict/list as JSON
    """
    enabled = request.config.getoption("--save-output")
    test_name = request.node.name
    test_output_dir = OUTPUT_DIR / test_name

    def _save(source, name=None):
        if not enabled:
            return
        test_output_dir.mkdir(parents=True, exist_ok=True)

        if isinstance(source, (dict, list)):
            # Save as JSON
            dest = test_output_dir / (name or "output.json")
            dest.write_text(json.dumps(source, indent=2, ensure_ascii=False))
        elif isinstance(source, Path) and source.is_dir():
            # Copy directory contents
            dest = test_output_dir / (name or source.name)
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(source, dest)
        elif isinstance(source, Path) and source.is_file():
            # Copy single file
            dest = test_output_dir / (name or source.name)
            shutil.copy2(source, dest)

    return _save


def pytest_configure(config):
    """Clean output directory at the start of a test run if --save-output is set."""
    if config.getoption("--save-output", default=False):
        if OUTPUT_DIR.exists():
            shutil.rmtree(OUTPUT_DIR)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
