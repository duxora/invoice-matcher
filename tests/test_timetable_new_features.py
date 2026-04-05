"""Tests for new timetable features: edit/delete, toggle, templates, iCal, i18n, activity log."""
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import date
from pathlib import Path


# --- i18n tests ---

def test_translator_english():
    from claude_scheduler.timetable.i18n import get_translator
    t = get_translator("en")
    assert t("family_timetable") == "Family Timetable"
    assert t("add_entry") == "Add Entry"


def test_translator_vietnamese():
    from claude_scheduler.timetable.i18n import get_translator
    t = get_translator("vi")
    assert t("family_timetable") == "Thoi Khoa Bieu Gia Dinh"
    assert t("add_entry") == "Them Muc"


def test_translator_fallback():
    from claude_scheduler.timetable.i18n import get_translator
    t = get_translator("xx")  # unknown language
    assert t("family_timetable") == "Family Timetable"  # falls back to English


def test_translator_missing_key():
    from claude_scheduler.timetable.i18n import get_translator
    t = get_translator("en")
    assert t("nonexistent_key") == "nonexistent_key"


# --- iCal tests ---

def test_ical_basic_export():
    from claude_scheduler.timetable.ical import entries_to_ical
    entries = [
        {"Date": "2026-03-09", "Time": "09:00", "Title": "Meeting", "Person": "Duc", "_type": "Tasks"},
    ]
    result = entries_to_ical(entries)
    assert "BEGIN:VCALENDAR" in result
    assert "BEGIN:VEVENT" in result
    assert "SUMMARY:Meeting" in result
    assert "DTSTART:20260309T090000" in result
    assert "END:VCALENDAR" in result


def test_ical_event_with_end_time():
    from claude_scheduler.timetable.ical import entries_to_ical
    entries = [
        {"Date": "2026-03-09", "Start Time": "14:00", "End Time": "16:00",
         "Title": "Party", "Participants": "Family", "_type": "Events"},
    ]
    result = entries_to_ical(entries)
    assert "DTSTART:20260309T140000" in result
    assert "DTEND:20260309T160000" in result


def test_ical_empty_entries():
    from claude_scheduler.timetable.ical import entries_to_ical
    result = entries_to_ical([])
    assert "BEGIN:VCALENDAR" in result
    assert "BEGIN:VEVENT" not in result


def test_ical_skip_invalid_date():
    from claude_scheduler.timetable.ical import entries_to_ical
    entries = [{"Date": "invalid", "Title": "Bad", "_type": "Tasks"}]
    result = entries_to_ical(entries)
    assert "BEGIN:VEVENT" not in result


# --- Schedule templates tests ---

def test_school_week_template():
    from claude_scheduler.timetable.schedule_templates import get_template_entries, TEMPLATES
    assert "school_week" in TEMPLATES
    entries = get_template_entries("school_week", "Child1", "2026-03-09")
    assert len(entries) > 0
    # Should have Study entries for Mon-Fri
    dates = {e["Date"] for e in entries}
    assert "2026-03-09" in dates  # Monday


def test_daily_routine_template():
    from claude_scheduler.timetable.schedule_templates import get_template_entries
    entries = get_template_entries("daily_routine", "Child1", "2026-03-09")
    assert len(entries) > 0
    # Daily routine applies to all 7 days
    dates = {e["Date"] for e in entries}
    assert len(dates) == 7


def test_weekend_family_template():
    from claude_scheduler.timetable.schedule_templates import get_template_entries
    entries = get_template_entries("weekend_family", "Duc", "2026-03-09")
    assert len(entries) > 0
    # Should have Saturday and Sunday entries
    for e in entries:
        d = date.fromisoformat(e["Date"])
        assert d.weekday() in (5, 6)  # Saturday or Sunday


def test_unknown_template():
    from claude_scheduler.timetable.schedule_templates import get_template_entries
    entries = get_template_entries("nonexistent", "Duc", "2026-03-09")
    assert entries == []


def test_get_sheet_for_entry():
    from claude_scheduler.timetable.schedule_templates import get_sheet_for_entry
    assert get_sheet_for_entry({"Subject": "Math"}) == "Study"
    assert get_sheet_for_entry({"Participants": "Family"}) == "Events"
    assert get_sheet_for_entry({"Title": "Chore"}) == "Tasks"


# --- Service: new methods ---

@pytest.fixture
def mock_sheets():
    client = MagicMock()
    client.fetch_by_date_range.return_value = []
    client.fetch_by_date.return_value = []
    client.fetch_sheet.return_value = []
    client.get_record.return_value = {}
    return client


def test_service_toggle_task(mock_sheets):
    from claude_scheduler.timetable.service import TimetableService
    mock_sheets.get_record.return_value = {
        "Date": "2026-03-09", "Time": "09:00", "Person": "Duc",
        "Title": "Task", "Description": "", "Status": "pending", "Recurring": ""
    }
    svc = TimetableService(mock_sheets, family_members=["Duc"])
    result = svc.toggle_task_status(0)
    assert result == "done"
    mock_sheets.update_row.assert_called_once()


def test_service_toggle_reminder(mock_sheets):
    from claude_scheduler.timetable.service import TimetableService
    mock_sheets.get_record.return_value = {
        "Date": "2026-03-09", "Time": "09:00", "Person": "Duc",
        "Title": "Remind", "Description": "", "Priority": "high", "Done": ""
    }
    svc = TimetableService(mock_sheets, family_members=["Duc"])
    result = svc.toggle_reminder_done(0)
    assert result == "yes"


def test_service_delete_entry(mock_sheets):
    from claude_scheduler.timetable.service import TimetableService
    mock_sheets.delete_row.return_value = {"Title": "Deleted"}
    svc = TimetableService(mock_sheets, family_members=["Duc"])
    result = svc.delete_entry("Tasks", 0)
    assert result["Title"] == "Deleted"
    mock_sheets.delete_row.assert_called_once_with("Tasks", 0)


def test_service_get_entry(mock_sheets):
    from claude_scheduler.timetable.service import TimetableService
    mock_sheets.get_record.return_value = {"Title": "Test"}
    svc = TimetableService(mock_sheets, family_members=["Duc"])
    result = svc.get_entry("Tasks", 0)
    assert result["Title"] == "Test"


def test_service_overdue_items(mock_sheets):
    from claude_scheduler.timetable.service import TimetableService
    mock_sheets.fetch_sheet.side_effect = lambda name: {
        "Tasks": [{"Date": "2026-03-01", "Status": "pending", "Title": "Old task"}],
        "Reminders": [{"Date": "2026-03-01", "Done": "", "Title": "Old reminder"}],
        "Study": [{"Deadline": "2026-03-01", "Title": "Old homework"}],
    }.get(name, [])
    svc = TimetableService(mock_sheets, family_members=["Duc"])
    overdue = svc.get_overdue_items("2026-03-09")
    assert len(overdue) == 3


def test_service_detect_conflicts(mock_sheets):
    from claude_scheduler.timetable.service import TimetableService
    # Only Tasks returns conflicting entries; Study and Events return empty
    mock_sheets.fetch_by_date.side_effect = lambda sheet, date: {
        "Tasks": [
            {"Date": "2026-03-09", "Time": "09:00", "Person": "Duc", "Title": "A"},
            {"Date": "2026-03-09", "Time": "09:00", "Person": "Duc", "Title": "B"},
        ],
        "Study": [],
        "Events": [],
    }.get(sheet, [])
    svc = TimetableService(mock_sheets, family_members=["Duc"])
    conflicts = svc.detect_conflicts("2026-03-09")
    assert len(conflicts) == 1


def test_service_member_filter_weekly(mock_sheets):
    from claude_scheduler.timetable.service import TimetableService
    mock_sheets.fetch_by_date_range.return_value = [
        {"Date": "2026-03-09", "Time": "09:00", "Person": "Duc", "Title": "A"},
        {"Date": "2026-03-09", "Time": "10:00", "Person": "Wife", "Title": "B"},
    ]
    svc = TimetableService(mock_sheets, family_members=["Duc", "Wife"])
    week = svc.get_week_data("2026-03-09", member="Duc")
    entries = week.get("2026-03-09", [])
    assert all(e.get("Person") == "Duc" for e in entries)


def test_service_all_entries_for_range(mock_sheets):
    from claude_scheduler.timetable.service import TimetableService
    mock_sheets.fetch_by_date_range.return_value = [
        {"Date": "2026-03-09", "Person": "Duc", "Title": "A"},
    ]
    svc = TimetableService(mock_sheets, family_members=["Duc"])
    entries = svc.get_all_entries_for_range("2026-03-09", "2026-03-15")
    assert len(entries) >= 1


# --- Sheets client: new methods ---

def test_sheets_get_record():
    from claude_scheduler.timetable.sheets import SheetsClient
    mock_ss = MagicMock()
    mock_ws = MagicMock()
    mock_ws.get_all_records.return_value = [
        {"Title": "First"}, {"Title": "Second"}
    ]
    mock_ss.worksheet.return_value = mock_ws

    with patch.object(SheetsClient, '_open_spreadsheet', return_value=mock_ss):
        client = SheetsClient(spreadsheet_id="fake", credentials_path="/fake.json")
        assert client.get_record("Tasks", 0)["Title"] == "First"
        assert client.get_record("Tasks", 1)["Title"] == "Second"
        assert client.get_record("Tasks", 99) == {}


def test_sheets_update_row():
    from claude_scheduler.timetable.sheets import SheetsClient
    mock_ss = MagicMock()
    mock_ws = MagicMock()
    mock_ss.worksheet.return_value = mock_ws

    with patch.object(SheetsClient, '_open_spreadsheet', return_value=mock_ss):
        client = SheetsClient(spreadsheet_id="fake", credentials_path="/fake.json")
        client.update_row("Tasks", 0, {
            "Date": "2026-03-09", "Time": "09:00", "Person": "Duc",
            "Title": "Updated", "Description": "", "Status": "done", "Recurring": ""
        })
    mock_ws.update.assert_called_once()


def test_sheets_delete_row():
    from claude_scheduler.timetable.sheets import SheetsClient
    mock_ss = MagicMock()
    mock_ws = MagicMock()
    mock_ws.get_all_records.return_value = [{"Title": "ToDelete"}]
    mock_ss.worksheet.return_value = mock_ws

    with patch.object(SheetsClient, '_open_spreadsheet', return_value=mock_ss):
        client = SheetsClient(spreadsheet_id="fake", credentials_path="/fake.json")
        deleted = client.delete_row("Tasks", 0)
    assert deleted["Title"] == "ToDelete"
    mock_ws.delete_rows.assert_called_once_with(2)  # row 0 -> sheet row 2


# --- Activity log ---

def test_activity_log(tmp_path):
    from claude_scheduler.timetable.sheets import _log_activity, get_activity_log, ACTIVITY_LOG_PATH

    test_log = tmp_path / "test-activity.jsonl"
    with patch("claude_scheduler.timetable.sheets.ACTIVITY_LOG_PATH", test_log):
        _log_activity("add", "Tasks", {"Title": "Test", "Date": "2026-03-09"})
        _log_activity("edit", "Tasks", {"Title": "Updated"})

        log = get_activity_log(limit=10)
    assert len(log) == 2
    assert log[0]["action"] == "edit"  # most recent first
    assert log[1]["action"] == "add"


# --- Route-level tests for new endpoints ---

@pytest.fixture
def route_client():
    from claude_scheduler.timetable.routes import router
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(router)
    yield TestClient(app)


def test_edit_form(route_client):
    with patch("claude_scheduler.timetable.routes.get_service") as mock:
        mock.return_value.get_entry.return_value = {
            "Date": "2026-03-09", "Time": "09:00", "Person": "Duc",
            "Title": "Test", "Description": "", "Status": "pending", "Recurring": ""
        }
        resp = route_client.get("/edit/Tasks/0")
    assert resp.status_code == 200


def test_edit_form_missing_entry(route_client):
    with patch("claude_scheduler.timetable.routes.get_service") as mock:
        mock.return_value.get_entry.return_value = {}
        resp = route_client.get("/edit/Tasks/99", follow_redirects=False)
    assert resp.status_code == 303


def test_save_edit(route_client):
    with patch("claude_scheduler.timetable.routes.get_service") as mock:
        resp = route_client.post("/edit/Tasks/0", data={
            "date": "2026-03-09", "time": "10:00", "person": "Duc",
            "title": "Updated", "status": "done",
        }, follow_redirects=False)
    assert resp.status_code == 303
    mock.return_value.update_entry.assert_called_once()


def test_delete_entry_route(route_client):
    with patch("claude_scheduler.timetable.routes.get_service") as mock:
        mock.return_value.delete_entry.return_value = {"Date": "2026-03-09"}
        resp = route_client.post("/delete/Tasks/0", follow_redirects=False)
    assert resp.status_code == 303


def test_toggle_task_route(route_client):
    with patch("claude_scheduler.timetable.routes.get_service") as mock:
        mock.return_value.toggle_task_status.return_value = "done"
        resp = route_client.post("/toggle/Tasks/0", follow_redirects=False)
    assert resp.status_code == 303


def test_toggle_reminder_route(route_client):
    with patch("claude_scheduler.timetable.routes.get_service") as mock:
        mock.return_value.toggle_reminder_done.return_value = "yes"
        resp = route_client.post("/toggle/Reminders/0", follow_redirects=False)
    assert resp.status_code == 303


def test_activity_log_page(route_client):
    with patch("claude_scheduler.timetable.routes.get_activity_log", return_value=[]):
        resp = route_client.get("/activity")
    assert resp.status_code == 200


def test_templates_page(route_client):
    resp = route_client.get("/templates")
    assert resp.status_code == 200


def test_apply_template(route_client):
    with patch("claude_scheduler.timetable.routes.get_service") as mock:
        resp = route_client.post("/apply-template", data={
            "template_id": "school_week",
            "person": "Child1",
            "start_date": "2026-03-09",
        }, follow_redirects=False)
    assert resp.status_code == 303
    # Should have called append_row multiple times for template entries
    assert mock.return_value.sheets.append_row.call_count > 0


def test_ical_export(route_client):
    with patch("claude_scheduler.timetable.routes.get_service") as mock:
        mock.return_value.get_all_entries_for_range.return_value = [
            {"Date": "2026-03-09", "Time": "09:00", "Title": "Test", "_type": "Tasks"},
        ]
        resp = route_client.get("/export.ics")
    assert resp.status_code == 200
    assert "BEGIN:VCALENDAR" in resp.text
    assert resp.headers["content-type"] == "text/calendar; charset=utf-8"


def test_ical_export_member_filter(route_client):
    with patch("claude_scheduler.timetable.routes.get_service") as mock:
        mock.return_value.get_all_entries_for_range.return_value = []
        resp = route_client.get("/export.ics?member=Duc")
    assert resp.status_code == 200


def test_colors_page(route_client):
    resp = route_client.get("/colors")
    assert resp.status_code == 200


def test_weekly_with_member_filter(route_client):
    with patch("claude_scheduler.timetable.routes.get_service") as mock:
        mock.return_value.get_week_data.return_value = {}
        mock.return_value.get_pending_reminders.return_value = []
        mock.return_value.get_overdue_items.return_value = []
        mock.return_value.detect_conflicts.return_value = []
        resp = route_client.get("/?member=Duc")
    assert resp.status_code == 200


def test_daily_with_member_filter(route_client):
    with patch("claude_scheduler.timetable.routes.get_service") as mock:
        mock.return_value.get_daily_agenda.return_value = {"Duc": []}
        mock.return_value.get_pending_reminders.return_value = []
        mock.return_value.detect_conflicts.return_value = []
        resp = route_client.get("/day/2026-03-09?member=Duc")
    assert resp.status_code == 200


# --- Deadline info ---

def test_deadline_info_overdue():
    from claude_scheduler.timetable.routes import deadline_info
    with patch("claude_scheduler.timetable.routes.date") as mock_date:
        mock_date.today.return_value = date(2026, 3, 15)
        mock_date.fromisoformat = date.fromisoformat
        result = deadline_info({"Deadline": "2026-03-10"})
    assert result["status"] == "overdue"
    assert result["days"] == 5


def test_deadline_info_due_today():
    from claude_scheduler.timetable.routes import deadline_info
    with patch("claude_scheduler.timetable.routes.date") as mock_date:
        mock_date.today.return_value = date(2026, 3, 10)
        mock_date.fromisoformat = date.fromisoformat
        result = deadline_info({"Deadline": "2026-03-10"})
    assert result["status"] == "due_today"


def test_deadline_info_upcoming():
    from claude_scheduler.timetable.routes import deadline_info
    with patch("claude_scheduler.timetable.routes.date") as mock_date:
        mock_date.today.return_value = date(2026, 3, 7)
        mock_date.fromisoformat = date.fromisoformat
        result = deadline_info({"Deadline": "2026-03-10"})
    assert result["status"] == "upcoming"
    assert result["days"] == 3


def test_deadline_info_empty():
    from claude_scheduler.timetable.routes import deadline_info
    assert deadline_info({}) == {}
    assert deadline_info({"Deadline": ""}) == {}


# --- Month view ---

def test_month_data_service():
    from claude_scheduler.timetable.service import TimetableService
    mock_sheets = MagicMock()
    mock_sheets.fetch_by_date_range.side_effect = lambda sheet, start, end: [
        {"Date": "2026-03-10", "Time": "09:00", "Person": "Duc", "Title": "Task 1"},
        {"Date": "2026-03-10", "Time": "14:00", "Person": "Wife", "Title": "Task 2"},
        {"Date": "2026-03-15", "Time": "10:00", "Person": "Duc", "Title": "Task 3"},
    ] if sheet == "Tasks" else []
    svc = TimetableService(mock_sheets, family_members=["Duc", "Wife"])
    result = svc.get_month_data(2026, 3)
    assert "2026-03-10" in result
    assert len(result["2026-03-10"]) == 2
    assert "2026-03-15" in result


def test_month_data_service_member_filter():
    from claude_scheduler.timetable.service import TimetableService
    mock_sheets = MagicMock()
    mock_sheets.fetch_by_date_range.side_effect = lambda sheet, start, end: [
        {"Date": "2026-03-10", "Time": "09:00", "Person": "Duc", "Title": "Task 1"},
        {"Date": "2026-03-10", "Time": "14:00", "Person": "Wife", "Title": "Task 2"},
    ] if sheet == "Tasks" else []
    svc = TimetableService(mock_sheets, family_members=["Duc", "Wife"])
    result = svc.get_month_data(2026, 3, member="Duc")
    assert len(result.get("2026-03-10", [])) == 1
    assert result["2026-03-10"][0]["Person"] == "Duc"


def test_month_view_route(route_client):
    with patch("claude_scheduler.timetable.routes.get_service") as mock:
        mock.return_value.get_month_data.return_value = {}
        resp = route_client.get("/month/2026/3")
    assert resp.status_code == 200
    assert "March 2026" in resp.text or "2026" in resp.text


def test_month_view_redirect(route_client):
    resp = route_client.get("/month", follow_redirects=False)
    assert resp.status_code == 307
    assert "/month/" in resp.headers["location"]


def test_month_view_with_member_filter(route_client):
    with patch("claude_scheduler.timetable.routes.get_service") as mock:
        mock.return_value.get_month_data.return_value = {}
        resp = route_client.get("/month/2026/3?member=Duc")
    assert resp.status_code == 200
