"""tests/test_db.py"""
import unittest
import tempfile
from pathlib import Path
from claude_scheduler.core.db import Database
from claude_scheduler.core.models import RunRecord, ErrorRecord, Ticket

class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = Database(Path(self.tmp) / "test.db")

    def tearDown(self):
        self.db.close()
        import shutil
        shutil.rmtree(self.tmp)

    def test_creates_tables(self):
        tables = self.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        names = {r[0] for r in tables}
        self.assertIn("task_runs", names)
        self.assertIn("task_errors", names)
        self.assertIn("remediation_tickets", names)
        self.assertIn("task_state", names)

    def test_record_run_start_and_complete(self):
        run_id = self.db.start_run("test-task", "/path/to.task", "/tmp/log.json")
        self.assertGreater(run_id, 0)
        self.db.complete_run(run_id, "success", exit_code=0)
        run = self.db.get_run(run_id)
        self.assertEqual(run.status, "success")
        self.assertEqual(run.exit_code, 0)
        self.assertIsNotNone(run.completed_at)

    def test_record_error(self):
        run_id = self.db.start_run("test-task", "/path/to.task", "/tmp/log.json")
        err_id = self.db.record_error("test-task", run_id, "exit_code",
                                       "command failed", "stderr output")
        self.assertGreater(err_id, 0)
        errors = self.db.get_errors("test-task")
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].error_type, "exit_code")

    def test_task_state_tracking(self):
        self.db.update_task_state("test-task", "success")
        state = self.db.get_task_state("test-task")
        self.assertEqual(state["last_status"], "success")
        self.assertEqual(state["total_runs"], 1)
        self.assertEqual(state["consecutive_failures"], 0)

        self.db.update_task_state("test-task", "failed")
        state = self.db.get_task_state("test-task")
        self.assertEqual(state["consecutive_failures"], 1)
        self.assertEqual(state["total_failures"], 1)

    def test_create_ticket(self):
        tid = self.db.create_ticket("test-task", 1, "something broke")
        self.assertGreater(tid, 0)
        ticket = self.db.get_ticket(tid)
        self.assertEqual(ticket.status, "open")
        self.assertEqual(ticket.task_name, "test-task")

    def test_update_ticket(self):
        tid = self.db.create_ticket("test-task", 1, "broke")
        self.db.update_ticket(tid, status="resolved",
                              resolution="fixed dep")
        ticket = self.db.get_ticket(tid)
        self.assertEqual(ticket.status, "resolved")
        self.assertIn("fixed dep", ticket.resolution)

    def test_run_history(self):
        for i in range(5):
            rid = self.db.start_run("test-task", "/path", "/log")
            self.db.complete_run(rid, "success" if i % 2 == 0 else "failed")
        history = self.db.get_run_history("test-task", limit=3)
        self.assertEqual(len(history), 3)

    def test_crash_recovery(self):
        run_id = self.db.start_run("test-task", "/path", "/log")
        # Simulate crash — run stays in 'running' state
        stale = self.db.recover_stale_runs(max_age_seconds=0)
        self.assertEqual(len(stale), 1)
        run = self.db.get_run(run_id)
        self.assertEqual(run.status, "crashed")

if __name__ == "__main__":
    unittest.main()
