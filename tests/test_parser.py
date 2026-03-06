"""tests/test_parser.py"""
import unittest
from pathlib import Path
from claude_scheduler.core.parser import parse_task
from claude_scheduler.core.models import Task

FIXTURES = Path(__file__).parent / "fixtures"

class TestParser(unittest.TestCase):
    def test_parses_all_fields(self):
        task = parse_task(FIXTURES / "valid.task")
        self.assertEqual(task.name, "Test Task")
        self.assertEqual(task.schedule, "daily 09:00")
        self.assertEqual(task.tools, "Read,Grep")
        self.assertEqual(task.max_turns, 3)
        self.assertEqual(task.timeout, 120)
        self.assertTrue(task.enabled)
        self.assertIn("test prompt", task.prompt)
        self.assertIn("multiple lines", task.prompt)

    def test_applies_defaults_for_minimal(self):
        task = parse_task(FIXTURES / "minimal.task")
        self.assertEqual(task.name, "Minimal Task")
        self.assertEqual(task.schedule, "every 2h")
        self.assertEqual(task.model, "claude-sonnet-4-6")
        self.assertEqual(task.max_turns, 10)
        self.assertEqual(task.retry, 0)

    def test_parses_disabled(self):
        task = parse_task(FIXTURES / "disabled.task")
        self.assertFalse(task.enabled)

    def test_parses_retry_fields(self):
        task = parse_task(FIXTURES / "with-retry.task")
        self.assertEqual(task.retry, 3)
        self.assertEqual(task.retry_delay, 30)
        self.assertEqual(task.on_failure, "retry")

    def test_parses_remediation_fields(self):
        task = parse_task(FIXTURES / "with-remediation.task")
        self.assertEqual(task.on_failure, "investigate")
        self.assertIn("npm install", task.remediation_tools)
        self.assertEqual(task.remediation_max_turns, 10)

    def test_slug_generation(self):
        task = parse_task(FIXTURES / "valid.task")
        self.assertEqual(task.slug, "test-task")

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            parse_task(Path("/nonexistent.task"))

    def test_missing_name_raises(self):
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".task", delete=False) as f:
            f.write("# schedule: daily 09:00\n---\nprompt\n")
            path = Path(f.name)
        with self.assertRaises(ValueError):
            parse_task(path)
        path.unlink()

if __name__ == "__main__":
    unittest.main()
