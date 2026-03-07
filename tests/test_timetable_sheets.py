"""Tests for Google Sheets client."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import date, time


@pytest.fixture
def mock_worksheet():
    ws = MagicMock()
    ws.get_all_records.return_value = [
        {"Date": "2026-03-07", "Time": "09:00", "Person": "Duc",
         "Title": "Buy groceries", "Description": "Weekly shopping",
         "Status": "pending", "Recurring": "weekly"},
        {"Date": "2026-03-07", "Time": "14:00", "Person": "Wife",
         "Title": "Doctor appointment", "Description": "",
         "Status": "pending", "Recurring": ""},
    ]
    return ws


@pytest.fixture
def mock_spreadsheet(mock_worksheet):
    ss = MagicMock()
    ss.worksheet.return_value = mock_worksheet
    return ss


def test_fetch_sheet_returns_records(mock_spreadsheet):
    from claude_scheduler.timetable.sheets import SheetsClient

    with patch.object(SheetsClient, '_open_spreadsheet', return_value=mock_spreadsheet):
        client = SheetsClient(spreadsheet_id="fake-id", credentials_path="/fake/creds.json")
        records = client.fetch_sheet("Tasks")

    assert len(records) == 2
    assert records[0]["Title"] == "Buy groceries"
    assert records[1]["Person"] == "Wife"


def test_fetch_by_date_filters(mock_spreadsheet):
    from claude_scheduler.timetable.sheets import SheetsClient

    with patch.object(SheetsClient, '_open_spreadsheet', return_value=mock_spreadsheet):
        client = SheetsClient(spreadsheet_id="fake-id", credentials_path="/fake/creds.json")
        records = client.fetch_by_date("Tasks", "2026-03-07")

    assert len(records) == 2


def test_fetch_by_person_filters(mock_spreadsheet):
    from claude_scheduler.timetable.sheets import SheetsClient

    with patch.object(SheetsClient, '_open_spreadsheet', return_value=mock_spreadsheet):
        client = SheetsClient(spreadsheet_id="fake-id", credentials_path="/fake/creds.json")
        records = client.fetch_by_person("Tasks", "Duc")

    assert len(records) == 1
    assert records[0]["Title"] == "Buy groceries"


def test_append_row(mock_spreadsheet):
    from claude_scheduler.timetable.sheets import SheetsClient

    with patch.object(SheetsClient, '_open_spreadsheet', return_value=mock_spreadsheet):
        client = SheetsClient(spreadsheet_id="fake-id", credentials_path="/fake/creds.json")
        client.append_row("Tasks", {
            "Date": "2026-03-08", "Time": "10:00", "Person": "Duc",
            "Title": "New task", "Description": "", "Status": "pending", "Recurring": ""
        })

    mock_spreadsheet.worksheet("Tasks").append_row.assert_called_once()


def test_update_row(mock_spreadsheet, mock_worksheet):
    from claude_scheduler.timetable.sheets import SheetsClient

    mock_worksheet.find.return_value = MagicMock(row=2)

    with patch.object(SheetsClient, '_open_spreadsheet', return_value=mock_spreadsheet):
        client = SheetsClient(spreadsheet_id="fake-id", credentials_path="/fake/creds.json")
        client.update_cell("Tasks", row=2, col=6, value="done")

    mock_worksheet.update_cell.assert_called_once_with(2, 6, "done")
