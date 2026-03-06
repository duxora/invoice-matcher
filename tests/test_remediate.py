"""tests/test_remediate.py"""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from claude_scheduler.core.remediate import build_remediation_prompt, remediate_error
from claude_scheduler.core.parser import parse_task
from claude_scheduler.core.db import Database

FIXTURES = Path(__file__).parent / "fixtures"

class TestBuildPrompt(unittest.TestCase):
    def test_includes_error_context(self):
        task = parse_task(FIXTURES / "with-remediation.task")
        prompt = build_remediation_prompt(
            task=task,
            error_message="npm ERR! missing dependency",
            stderr_output="npm ERR! peer dep not found",
            attempt=2,
            consecutive_failures=3,
        )
        self.assertIn("npm ERR! missing dependency", prompt)
        self.assertIn("attempt 2", prompt.lower())
        self.assertIn("Remediation Task", prompt)
        self.assertIn("npm ERR! peer dep not found", prompt)

    def test_includes_user_guidance(self):
        task = parse_task(FIXTURES / "with-remediation.task")
        prompt = build_remediation_prompt(
            task=task,
            error_message="failed",
            stderr_output="",
            user_guidance="try running npm cache clean",
        )
        self.assertIn("npm cache clean", prompt)

class TestRemediate(unittest.TestCase):
    @patch("claude_scheduler.core.remediate.subprocess.run")
    def test_successful_remediation(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=b'{"result":"Fixed: installed missing dep"}',
            stderr=b"")
        task = parse_task(FIXTURES / "with-remediation.task")
        result = remediate_error(
            task=task,
            error_message="missing dep",
            stderr_output="npm ERR!",
        )
        self.assertTrue(result["success"])
        self.assertIn("Fixed", result["output"])

    @patch("claude_scheduler.core.remediate.subprocess.run")
    def test_failed_remediation_needs_user(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout=b'{"result":"Need user to update .npmrc"}',
            stderr=b"cannot fix automatically")
        task = parse_task(FIXTURES / "with-remediation.task")
        result = remediate_error(
            task=task,
            error_message="auth error",
            stderr_output="401 unauthorized",
        )
        self.assertFalse(result["success"])
        self.assertTrue(result["needs_user"])

if __name__ == "__main__":
    unittest.main()
