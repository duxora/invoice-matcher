"""Timetable data service -- aggregates sheets data for views."""
import calendar
from collections import defaultdict
from datetime import date, timedelta
from typing import Any


class TimetableService:
    """Business logic layer between Sheets and web routes."""

    def __init__(self, sheets_client, family_members: list[str]):
        self.sheets = sheets_client
        self.members = family_members

    def get_week_data(self, start_date_str: str, member: str = "") -> dict[str, list[dict]]:
        """Get all entries for a week, grouped by date. Optionally filter by member."""
        start = date.fromisoformat(start_date_str)
        start = start - timedelta(days=start.weekday())
        end = start + timedelta(days=6)

        result: dict[str, list[dict]] = defaultdict(list)
        for sheet_name in ("Tasks", "Study", "Reminders", "Events"):
            records = self.sheets.fetch_by_date_range(
                sheet_name, start.isoformat(), end.isoformat()
            )
            for r in records:
                r["_type"] = sheet_name
                if member and r.get("Person", r.get("Participants", "")) != member:
                    continue
                result[r.get("Date", "")].append(r)

        for d in result:
            result[d].sort(key=lambda r: r.get("Time", r.get("Start Time", "")))

        return dict(result)

    def get_month_data(self, year: int, month: int, member: str = "") -> dict[str, list[dict]]:
        """Get all entries for a month, grouped by date string."""
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])

        result: dict[str, list[dict]] = defaultdict(list)
        for sheet_name in ("Tasks", "Study", "Reminders", "Events"):
            records = self.sheets.fetch_by_date_range(
                sheet_name, first_day.isoformat(), last_day.isoformat()
            )
            for r in records:
                r["_type"] = sheet_name
                if member and r.get("Person", r.get("Participants", "")) != member:
                    continue
                result[r.get("Date", "")].append(r)

        for d in result:
            result[d].sort(key=lambda r: r.get("Time", r.get("Start Time", "")))

        return dict(result)

    def get_daily_agenda(self, date_str: str, member: str = "") -> dict[str, list[dict]]:
        """Get all entries for a day, grouped by person."""
        result: dict[str, list[dict]] = {m: [] for m in self.members}
        result["Family"] = []

        for sheet_name in ("Tasks", "Study", "Reminders", "Events"):
            records = self.sheets.fetch_by_date(sheet_name, date_str)
            for r in records:
                r["_type"] = sheet_name
                person = r.get("Person", r.get("Participants", "Family"))
                if member and person != member:
                    continue
                if person in result:
                    result[person].append(r)
                else:
                    result["Family"].append(r)

        for person in result:
            result[person].sort(key=lambda r: r.get("Time", r.get("Start Time", "")))

        return result

    def get_pending_reminders(self) -> list[dict[str, Any]]:
        """Get all unfinished reminders."""
        records = self.sheets.fetch_sheet("Reminders")
        return [r for r in records if not r.get("Done")]

    def get_entry(self, sheet_name: str, row_index: int) -> dict[str, Any]:
        """Get a single entry by sheet and row index."""
        return self.sheets.get_record(sheet_name, row_index)

    def update_entry(self, sheet_name: str, row_index: int, data: dict[str, Any]) -> None:
        """Update an existing entry."""
        self.sheets.update_row(sheet_name, row_index, data)

    def delete_entry(self, sheet_name: str, row_index: int) -> dict:
        """Delete an entry. Returns the deleted record."""
        return self.sheets.delete_row(sheet_name, row_index)

    def toggle_task_status(self, row_index: int) -> str:
        """Toggle task status between pending and done. Returns new status."""
        record = self.sheets.get_record("Tasks", row_index)
        current = record.get("Status", "pending")
        new_status = "done" if current != "done" else "pending"
        record["Status"] = new_status
        self.sheets.update_row("Tasks", row_index, record)
        return new_status

    def toggle_reminder_done(self, row_index: int) -> str:
        """Toggle reminder done status. Returns new value."""
        record = self.sheets.get_record("Reminders", row_index)
        current = record.get("Done", "")
        new_val = "" if current else "yes"
        record["Done"] = new_val
        self.sheets.update_row("Reminders", row_index, record)
        return new_val

    def get_overdue_items(self, today_str: str = "") -> list[dict]:
        """Get tasks/reminders/study items that are past their date or deadline."""
        if not today_str:
            today_str = date.today().isoformat()

        overdue = []
        # Overdue tasks
        for r in self.sheets.fetch_sheet("Tasks"):
            if r.get("Date", "") < today_str and r.get("Status", "") != "done":
                r["_type"] = "Tasks"
                overdue.append(r)

        # Overdue reminders
        for r in self.sheets.fetch_sheet("Reminders"):
            if r.get("Date", "") < today_str and not r.get("Done"):
                r["_type"] = "Reminders"
                overdue.append(r)

        # Overdue study deadlines
        for r in self.sheets.fetch_sheet("Study"):
            if r.get("Deadline") and r.get("Deadline") < today_str:
                r["_type"] = "Study"
                overdue.append(r)

        return overdue

    def detect_conflicts(self, date_str: str) -> list[tuple[dict, dict]]:
        """Find overlapping time entries for the same person on a given date."""
        entries_by_person: dict[str, list[dict]] = defaultdict(list)

        for sheet_name in ("Tasks", "Study", "Events"):
            records = self.sheets.fetch_by_date(sheet_name, date_str)
            for r in records:
                r["_type"] = sheet_name
                person = r.get("Person", r.get("Participants", ""))
                time_str = r.get("Time", r.get("Start Time", ""))
                if person and time_str:
                    entries_by_person[person].append(r)

        conflicts = []
        for person, entries in entries_by_person.items():
            entries.sort(key=lambda r: r.get("Time", r.get("Start Time", "")))
            for i in range(len(entries) - 1):
                t1 = entries[i].get("Time", entries[i].get("Start Time", ""))
                t2 = entries[i + 1].get("Time", entries[i + 1].get("Start Time", ""))
                if t1 == t2:
                    conflicts.append((entries[i], entries[i + 1]))

        return conflicts

    def generate_recurring(self, from_date_str: str, weeks: int = 1) -> int:
        """Generate recurring task instances for future dates. Returns count of created entries."""
        tasks = self.sheets.fetch_sheet("Tasks")
        recurring_tasks = [t for t in tasks if t.get("Recurring")]
        count = 0
        from_date = date.fromisoformat(from_date_str)

        for task in recurring_tasks:
            recurring_type = task["Recurring"]
            for week in range(1, weeks + 1):
                if recurring_type == "daily":
                    for day in range(7):
                        new_date = from_date + timedelta(days=week * 7 + day)
                        self._create_recurring_instance(task, new_date.isoformat())
                        count += 1
                elif recurring_type == "weekly":
                    new_date = from_date + timedelta(weeks=week)
                    self._create_recurring_instance(task, new_date.isoformat())
                    count += 1
                elif recurring_type == "monthly":
                    # Approximate: add 30 days per month
                    new_date = from_date + timedelta(days=30 * week)
                    self._create_recurring_instance(task, new_date.isoformat())
                    count += 1

        return count

    def _create_recurring_instance(self, task: dict, date_str: str) -> None:
        """Create a single instance of a recurring task."""
        new_task = {
            "Date": date_str,
            "Time": task.get("Time", ""),
            "Person": task.get("Person", ""),
            "Title": task.get("Title", ""),
            "Description": task.get("Description", ""),
            "Status": "pending",
            "Recurring": "",  # Instance is not itself recurring
        }
        self.sheets.append_row("Tasks", new_task)

    def get_all_entries_for_range(self, start: str, end: str, member: str = "") -> list[dict]:
        """Get flat list of all entries in a date range, for iCal export."""
        entries = []
        for sheet_name in ("Tasks", "Study", "Reminders", "Events"):
            records = self.sheets.fetch_by_date_range(sheet_name, start, end)
            for r in records:
                r["_type"] = sheet_name
                person = r.get("Person", r.get("Participants", ""))
                if member and person != member:
                    continue
                entries.append(r)
        return entries
