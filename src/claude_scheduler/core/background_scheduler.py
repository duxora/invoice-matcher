"""Background scheduler — runs inside the FastAPI process via asyncio."""
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from croniter import croniter

from .models import Task
from .parser import find_tasks

logger = logging.getLogger("claude_scheduler.bg")

DAY_MAP = {"mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 0}


def schedule_to_cron(schedule: str) -> str | None:
    """Convert task schedule format to a 5-field cron expression."""
    import re

    m = re.match(r"^daily (\d{2}):(\d{2})$", schedule)
    if m:
        return f"{int(m[2])} {int(m[1])} * * *"

    m = re.match(r"^weekly (\w+) (\d{2}):(\d{2})$", schedule)
    if m:
        wd = DAY_MAP.get(m[1].lower(), 1)
        return f"{int(m[3])} {int(m[2])} * * {wd}"

    m = re.match(r"^every (\d+)h$", schedule)
    if m:
        return f"0 */{int(m[1])} * * *"

    m = re.match(r"^every (\d+)m$", schedule)
    if m:
        return f"*/{int(m[1])} * * * *"

    return None


def _run_task_sync(task: Task, tasks_dir: Path, logs_dir: Path, data_dir: Path):
    """Run a single task synchronously (called in a thread)."""
    from .db import Database
    from .orchestrator import Orchestrator

    db = Database(data_dir / "scheduler.db")
    try:
        orch = Orchestrator(tasks_dir=tasks_dir, logs_dir=logs_dir, db=db)
        logger.info("Running scheduled task: %s", task.name)
        orch.run_single(task)
        state = db.get_task_state(task.name)
        status = state["last_status"] if state else "unknown"
        logger.info("Task %s finished: %s", task.name, status)
    except Exception:
        logger.exception("Task %s failed with exception", task.name)
    finally:
        db.close()


async def scheduler_loop(tasks_dir: Path, logs_dir: Path, data_dir: Path):
    """Main scheduler loop — checks every 30s if any task is due."""
    logger.info("Background scheduler started (tasks_dir=%s)", tasks_dir)

    # Track last fire time per task slug to avoid double-firing within same minute
    last_fired: dict[str, datetime] = {}

    while True:
        try:
            now = datetime.now()
            tasks = [t for t in find_tasks(tasks_dir) if t.enabled]

            for task in tasks:
                cron_expr = schedule_to_cron(task.schedule)
                if not cron_expr:
                    continue

                cron = croniter(cron_expr, now)
                prev_fire = cron.get_prev(datetime)

                # Task is due if prev_fire is within the last 60s
                # and we haven't already fired it this minute
                elapsed = (now - prev_fire).total_seconds()
                if elapsed <= 60:
                    slug = task.slug
                    if slug in last_fired:
                        diff = (now - last_fired[slug]).total_seconds()
                        if diff < 120:
                            continue  # already fired recently

                    last_fired[slug] = now
                    logger.info("Task %s is due (schedule=%s, cron=%s)",
                                task.name, task.schedule, cron_expr)

                    # Run in thread to avoid blocking the event loop
                    loop = asyncio.get_running_loop()
                    loop.run_in_executor(
                        None, _run_task_sync,
                        task, tasks_dir, logs_dir, data_dir,
                    )

        except Exception:
            logger.exception("Scheduler loop error")

        await asyncio.sleep(30)
