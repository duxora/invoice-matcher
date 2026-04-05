"""tests/test_integration.py"""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from claude_scheduler.core.parser import parse_task, find_tasks
from claude_scheduler.core.db import Database
from claude_scheduler.core.orchestrator import Orchestrator

FIXTURES = Path(__file__).parent / "fixtures"

class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = Database(Path(self.tmp) / "test.db")

    def tearDown(self):
        self.db.close()
        import shutil; shutil.rmtree(self.tmp)

    def test_full_parse_to_db_flow(self):
        task = parse_task(FIXTURES / "valid.task")
        self.assertEqual(task.name, "Test Task")
        run_id = self.db.start_run(task.name, str(task.file_path), "/tmp/log")
        self.db.complete_run(run_id, "success", exit_code=0)
        self.db.update_task_state(task.name, "success")
        state = self.db.get_task_state(task.name)
        self.assertEqual(state["total_runs"], 1)

    @patch("claude_scheduler.core.orchestrator.run_with_retry")
    def test_orchestrator_end_to_end(self, mock_run):
        mock_run.return_value = {
            "status": "success", "exit_code": 0, "attempt": 1,
            "log_file": "/tmp/log", "stderr": "", "stdout": ""}
        orch = Orchestrator(FIXTURES, Path(self.tmp) / "logs", self.db)
        tasks = orch.find_tasks("daily")
        for task in tasks:
            orch.run_single(task)
        history = self.db.get_run_history()
        self.assertGreater(len(history), 0)

    def test_find_tasks_filters_disabled(self):
        tasks = find_tasks(FIXTURES)
        enabled = [t for t in tasks if t.enabled]
        names = [t.name for t in enabled]
        self.assertNotIn("Disabled Task", names)

    @patch("claude_scheduler.core.orchestrator.run_with_retry")
    @patch("claude_scheduler.core.orchestrator.remediate_error")
    @patch("claude_scheduler.core.orchestrator.notify_error")
    @patch("claude_scheduler.core.orchestrator.notify_ticket")
    def test_failure_creates_ticket(self, mock_nt, mock_ne, mock_rem, mock_run):
        mock_run.return_value = {
            "status": "failed", "exit_code": 1, "attempt": 1,
            "log_file": "/tmp/log", "stderr": "err", "stdout": "",
            "error_message": "crash"}
        mock_rem.return_value = {
            "success": False, "needs_user": True,
            "output": "NEEDS_USER: check it", "stderr": ""}
        task = parse_task(FIXTURES / "with-remediation.task")
        orch = Orchestrator(FIXTURES, Path(self.tmp) / "logs", self.db)
        orch.run_single(task)
        tickets = self.db.get_tickets(status="open")
        self.assertEqual(len(tickets), 1)
        self.assertEqual(tickets[0].task_name, "Remediation Task")

if __name__ == "__main__":
    unittest.main()
