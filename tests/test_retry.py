"""tests/test_retry.py"""
import unittest
from unittest.mock import patch, MagicMock, call
from pathlib import Path
from claude_scheduler.core.retry import run_with_retry
from claude_scheduler.core.parser import parse_task

FIXTURES = Path(__file__).parent / "fixtures"

class TestRetry(unittest.TestCase):
    @patch("claude_scheduler.core.retry.execute_task")
    def test_no_retry_on_success(self, mock_exec):
        mock_exec.return_value = {"status": "success", "exit_code": 0,
                                   "log_file": "/tmp/log", "stderr": "", "stdout": ""}
        task = parse_task(FIXTURES / "with-retry.task")
        result = run_with_retry(task, Path("/tmp"))
        self.assertEqual(mock_exec.call_count, 1)
        self.assertEqual(result["status"], "success")

    @patch("claude_scheduler.core.retry.time.sleep")
    @patch("claude_scheduler.core.retry.execute_task")
    def test_retries_on_failure(self, mock_exec, mock_sleep):
        mock_exec.side_effect = [
            {"status": "failed", "exit_code": 1, "log_file": "/tmp/log",
             "stderr": "err", "stdout": "", "error_message": "failed"},
            {"status": "failed", "exit_code": 1, "log_file": "/tmp/log",
             "stderr": "err", "stdout": "", "error_message": "failed"},
            {"status": "success", "exit_code": 0, "log_file": "/tmp/log",
             "stderr": "", "stdout": ""},
        ]
        task = parse_task(FIXTURES / "with-retry.task")
        result = run_with_retry(task, Path("/tmp"))
        self.assertEqual(mock_exec.call_count, 3)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["attempt"], 3)

    @patch("claude_scheduler.core.retry.time.sleep")
    @patch("claude_scheduler.core.retry.execute_task")
    def test_exhausts_retries(self, mock_exec, mock_sleep):
        mock_exec.return_value = {"status": "failed", "exit_code": 1,
            "log_file": "/tmp/log", "stderr": "err", "stdout": "",
            "error_message": "failed"}
        task = parse_task(FIXTURES / "with-retry.task")  # retry: 3
        result = run_with_retry(task, Path("/tmp"))
        # 1 initial + 3 retries = 4 total
        self.assertEqual(mock_exec.call_count, 4)
        self.assertEqual(result["status"], "failed")

    @patch("claude_scheduler.core.retry.time.sleep")
    @patch("claude_scheduler.core.retry.execute_task")
    def test_exponential_backoff(self, mock_exec, mock_sleep):
        mock_exec.return_value = {"status": "failed", "exit_code": 1,
            "log_file": "/tmp/log", "stderr": "err", "stdout": "",
            "error_message": "failed"}
        task = parse_task(FIXTURES / "with-retry.task")  # retry_delay: 30
        run_with_retry(task, Path("/tmp"))
        delays = [c.args[0] for c in mock_sleep.call_args_list]
        self.assertEqual(delays, [30, 60, 120])  # 30 * 2^0, 2^1, 2^2

    @patch("claude_scheduler.core.retry.execute_task")
    def test_no_retry_when_retry_is_zero(self, mock_exec):
        mock_exec.return_value = {"status": "failed", "exit_code": 1,
            "log_file": "/tmp/log", "stderr": "", "stdout": "",
            "error_message": "failed"}
        task = parse_task(FIXTURES / "minimal.task")  # retry: 0 (default)
        result = run_with_retry(task, Path("/tmp"))
        self.assertEqual(mock_exec.call_count, 1)

if __name__ == "__main__":
    unittest.main()
