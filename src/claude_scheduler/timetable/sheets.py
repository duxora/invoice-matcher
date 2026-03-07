"""Google Sheets client for Family Timetable."""
import time as _time
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


class SheetsClient:
    """Two-way sync client for Google Sheets."""

    def __init__(self, spreadsheet_id: str, credentials_path: str):
        self.spreadsheet_id = spreadsheet_id
        self.credentials_path = credentials_path
        self._spreadsheet = self._open_spreadsheet()
        self._cache: dict[str, tuple[float, list[dict]]] = {}
        self._cache_ttl = 60  # seconds

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

        ws = self._spreadsheet.worksheet(sheet_name)
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
        ws = self._spreadsheet.worksheet(sheet_name)
        columns = SHEET_COLUMNS.get(sheet_name, list(data.keys()))
        row = [data.get(col, "") for col in columns]
        ws.append_row(row)
        self._invalidate_cache(sheet_name)

    def update_cell(self, sheet_name: str, row: int, col: int, value: str) -> None:
        """Update a single cell."""
        ws = self._spreadsheet.worksheet(sheet_name)
        ws.update_cell(row, col, value)
        self._invalidate_cache(sheet_name)

    def _invalidate_cache(self, sheet_name: str) -> None:
        self._cache.pop(sheet_name, None)
