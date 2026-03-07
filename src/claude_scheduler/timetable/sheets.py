"""Google Sheets client for Family Timetable."""
import json
import time as _time
from datetime import datetime
from pathlib import Path
from typing import Any

import gspread
from google.oauth2.service_account import Credentials


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

SHEET_COLUMNS = {
    "Tasks": ["Date", "Time", "Person", "Title", "Description", "Status", "Recurring"],
    "Study": ["Date", "Time", "Person", "Subject", "Topic", "Type", "Deadline"],
    "Reminders": ["Date", "Time", "Person", "Title", "Description", "Priority", "Done"],
    "Events": ["Date", "Start Time", "End Time", "Title", "Description", "Participants"],
}

# Activity log stored locally (append-only JSONL)
ACTIVITY_LOG_PATH = Path("~/.config/claude-scheduler/timetable-activity.jsonl").expanduser()


def _log_activity(action: str, sheet_name: str, data: dict) -> None:
    """Append an activity entry to the local log."""
    ACTIVITY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "sheet": sheet_name,
        "data": {k: str(v) for k, v in data.items() if not k.startswith("_")},
    }
    with open(ACTIVITY_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def get_activity_log(limit: int = 50) -> list[dict]:
    """Read recent activity log entries."""
    if not ACTIVITY_LOG_PATH.exists():
        return []
    lines = ACTIVITY_LOG_PATH.read_text().strip().split("\n")
    entries = []
    for line in reversed(lines[-limit:]):
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


class SheetsClient:
    """Two-way sync client for Google Sheets."""

    def __init__(self, spreadsheet_id: str, credentials_path: str):
        self.spreadsheet_id = spreadsheet_id
        self.credentials_path = credentials_path
        self._spreadsheet = None
        self._cache: dict[str, tuple[float, list[dict]]] = {}
        self._cache_ttl = 60  # seconds

    @property
    def spreadsheet(self):
        """Lazy connection to Google Sheets."""
        if self._spreadsheet is None:
            self._spreadsheet = self._open_spreadsheet()
        return self._spreadsheet

    def _open_spreadsheet(self):
        creds = Credentials.from_service_account_file(self.credentials_path, scopes=SCOPES)
        gc = gspread.authorize(creds)
        return gc.open_by_key(self.spreadsheet_id)

    def fetch_sheet(self, sheet_name: str) -> list[dict[str, Any]]:
        """Fetch all records from a sheet, with caching."""
        now = _time.time()
        if sheet_name in self._cache:
            cached_time, cached_data = self._cache[sheet_name]
            if now - cached_time < self._cache_ttl:
                return cached_data

        ws = self.spreadsheet.worksheet(sheet_name)
        records = ws.get_all_records()
        self._cache[sheet_name] = (now, records)
        return records

    def fetch_by_date(self, sheet_name: str, date_str: str) -> list[dict[str, Any]]:
        """Fetch records filtered by date."""
        records = self.fetch_sheet(sheet_name)
        return [r for r in records if r.get("Date") == date_str]

    def fetch_by_person(self, sheet_name: str, person: str) -> list[dict[str, Any]]:
        """Fetch records filtered by person."""
        records = self.fetch_sheet(sheet_name)
        return [r for r in records if r.get("Person") == person]

    def fetch_by_date_range(self, sheet_name: str, start: str, end: str) -> list[dict[str, Any]]:
        """Fetch records within a date range (inclusive)."""
        records = self.fetch_sheet(sheet_name)
        return [r for r in records if start <= r.get("Date", "") <= end]

    def append_row(self, sheet_name: str, data: dict[str, Any]) -> None:
        """Append a new row to a sheet."""
        ws = self.spreadsheet.worksheet(sheet_name)
        columns = SHEET_COLUMNS.get(sheet_name, list(data.keys()))
        row = [data.get(col, "") for col in columns]
        ws.append_row(row)
        self._invalidate_cache(sheet_name)
        _log_activity("add", sheet_name, data)

    def update_row(self, sheet_name: str, row_index: int, data: dict[str, Any]) -> None:
        """Update an entire row (row_index is 1-based, header is row 1, data starts at row 2)."""
        ws = self.spreadsheet.worksheet(sheet_name)
        columns = SHEET_COLUMNS.get(sheet_name, list(data.keys()))
        values = [data.get(col, "") for col in columns]
        # row_index is the data row (0-based from records), sheet row = row_index + 2 (header + 1-based)
        sheet_row = row_index + 2
        cell_range = f"A{sheet_row}:{chr(64 + len(columns))}{sheet_row}"
        ws.update(cell_range, [values])
        self._invalidate_cache(sheet_name)
        _log_activity("edit", sheet_name, data)

    def delete_row(self, sheet_name: str, row_index: int) -> dict:
        """Delete a row. Returns the deleted record for logging."""
        records = self.fetch_sheet(sheet_name)
        deleted = records[row_index] if row_index < len(records) else {}
        ws = self.spreadsheet.worksheet(sheet_name)
        sheet_row = row_index + 2
        ws.delete_rows(sheet_row)
        self._invalidate_cache(sheet_name)
        _log_activity("delete", sheet_name, deleted)
        return deleted

    def update_cell(self, sheet_name: str, row: int, col: int, value: str) -> None:
        """Update a single cell."""
        ws = self.spreadsheet.worksheet(sheet_name)
        ws.update_cell(row, col, value)
        self._invalidate_cache(sheet_name)

    def get_record(self, sheet_name: str, row_index: int) -> dict[str, Any]:
        """Get a single record by row index (0-based)."""
        records = self.fetch_sheet(sheet_name)
        if 0 <= row_index < len(records):
            return records[row_index]
        return {}

    def _invalidate_cache(self, sheet_name: str) -> None:
        self._cache.pop(sheet_name, None)
