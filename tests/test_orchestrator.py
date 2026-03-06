"""tests/test_orchestrator.py"""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from claude_scheduler.core.orchestrator import Orchestrator
from claude_scheduler.core.db import Database

FIXTURES = Path(__file__).parent / "fixtures"

class TestOrchestrator(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = Database(Path(self.tmp) / "test.db")
        self.orch = Orchestrator(
            tasks_dir=FIXTURES, logs_dir=Path(self.tmp) / "logs",
            db=self.db)

    def tearDown(self):
        self.db.close()
        import shutil; shutil.rmtree(self.tmp)

    def test_finds_tasks_by_schedule(self):
        daily = self.orch.find_tasks(schedule_type="daily")
        self.assertTrue(any(t.name == "Test Task" for t in daily))
        self.assertFalse(any(t.name == "Disabled Task" for t in daily))

    def test_skips_disabled_tasks(self):
        all_tasks = self.orch.find_tasks(schedule_type="all")
        self.assertFalse(any(t.name == "Disabled Task" for t in all_tasks))

    @patch("claude_scheduler.core.orchestrator.run_with_retry")
    @patch("claude_scheduler.core.orchestrator.notify_error")
    def test_run_task_records_success(self, mock_notify, mock_run):
        mock_run.return_value = {
            "status": "success", "exit_code": 0, "attempt": 1,
            "log_file": "/tmp/log", "stderr": "", "stdout": ""}
        from claude_scheduler.core.parser import parse_task
        task = parse_task(FIXTURES / "valid.task")
        self.orch.run_single(task)
        state = self.db.get_task_state("Test Task")
        self.assertEqual(state["last_status"], "success")
        mock_notify.assert_not_called()

    @patch("claude_scheduler.core.orchestrator.notify_ticket")
    @patch("claude_scheduler.core.orchestrator.remediate_error")
    @patch("claude_scheduler.core.orchestrator.notify_error")
    @patch("claude_scheduler.core.orchestrator.run_with_retry")
    def test_run_task_triggers_remediation(self, mock_run, mock_notify, mock_rem, mock_ticket):
        mock_run.return_value = {
            "status": "failed", "exit_code": 1, "attempt": 1,
            "log_file": "/tmp/log", "stderr": "err", "stdout": "",
            "error_message": "failed"}
        mock_rem.return_value = {
            "success": False, "needs_user": True,
            "output": "NEEDS_USER: check config", "stderr": "", "exit_code": 1}
        from claude_scheduler.core.parser import parse_task
        task = parse_task(FIXTURES / "with-remediation.task")
        self.orch.run_single(task)
        mock_rem.assert_called_once()
        tickets = self.db.get_tickets(status="open")
        self.assertEqual(len(tickets), 1)

    @patch("claude_scheduler.core.orchestrator.run_with_retry")
    def test_crash_recovery_on_init(self, mock_run):
        self.db.start_run("old-task", "/path", "/log")
        stale = self.db.recover_stale_runs(max_age_seconds=0)
        self.assertEqual(len(stale), 1)

if __name__ == "__main__":
    unittest.main()
