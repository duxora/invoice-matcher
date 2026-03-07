"""Timetable data service — aggregates sheets data for views."""
from collections import defaultdict
from datetime import date, timedelta
from typing import Any


class TimetableService:
    """Business logic layer between Sheets and web routes."""

    def __init__(self, sheets_client, family_members: list[str]):
        self.sheets = sheets_client
        self.members = family_members

    def get_week_data(self, start_date_str: str) -> dict[str, list[dict]]:
        """Get all entries for a week, grouped by date."""
        start = date.fromisoformat(start_date_str)
        # Align to Monday
        start = start - timedelta(days=start.weekday())
        end = start + timedelta(days=6)

        result: dict[str, list[dict]] = defaultdict(list)
        for sheet_name in ("Tasks", "Study", "Reminders", "Events"):
            records = self.sheets.fetch_by_date_range(
                sheet_name, start.isoformat(), end.isoformat()
            )
            for r in records:
                r["_type"] = sheet_name
                result[r.get("Date", "")].append(r)

        # Sort each day's entries by time
        for d in result:
            result[d].sort(key=lambda r: r.get("Time", r.get("Start Time", "")))

        return dict(result)

    def get_daily_agenda(self, date_str: str) -> dict[str, list[dict]]:
        """Get all entries for a day, grouped by person."""
        result: dict[str, list[dict]] = {m: [] for m in self.members}
        result["Family"] = []

        for sheet_name in ("Tasks", "Study", "Reminders", "Events"):
            records = self.sheets.fetch_by_date(sheet_name, date_str)
            for r in records:
                r["_type"] = sheet_name
                person = r.get("Person", r.get("Participants", "Family"))
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
