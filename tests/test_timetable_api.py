"""Tests for timetable JSON API endpoints."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def api_client():
    from claude_scheduler.timetable.api import api_router
    app = FastAPI()
    app.include_router(api_router)
    yield TestClient(app)


# --- Helpers ---

def _mock_service():
    """Create a mock TimetableService with common defaults."""
    svc = MagicMock()
    svc.get_week_data.return_value = {}
    svc.get_pending_reminders.return_value = []
    svc.get_overdue_items.return_value = []
    svc.detect_conflicts.return_value = []
    svc.get_daily_agenda.return_value = {}
    svc.get_month_data.return_value = {}
    svc.get_all_entries_for_range.return_value = []
    svc.sheets.fetch_sheet.return_value = []
    return svc


# --- 1. GET /api/config ---

def test_config_returns_family_members(api_client):
    resp = api_client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "family_members" in data
    assert "colors" in data
    assert "color_presets" in data
    assert "lang" in data
    assert "translations" in data
    assert "sheets" in data
    assert data["sheets"] == ["Tasks", "Study", "Reminders", "Events"]


# --- 2. GET /api/week ---

def test_week_returns_7_days(api_client):
    svc = _mock_service()
    with patch("claude_scheduler.timetable.api.get_service", return_value=svc):
        resp = api_client.get("/api/week?start=2026-03-09")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["days"]) == 7
    assert "reminders" in data
    assert "overdue" in data
    assert "conflicts" in data
    assert "prev_week" in data
    assert "next_week" in data
    assert "week_label" in data
    assert "today" in data


def test_week_with_member_filter(api_client):
    svc = _mock_service()
    with patch("claude_scheduler.timetable.api.get_service", return_value=svc):
        resp = api_client.get("/api/week?start=2026-03-09&member=Duc")
    assert resp.status_code == 200
    svc.get_week_data.assert_called_once()
    assert svc.get_week_data.call_args[1]["member"] == "Duc"


def test_week_error_returns_500(api_client):
    svc = _mock_service()
    svc.get_week_data.side_effect = Exception("sheets error")
    with patch("claude_scheduler.timetable.api.get_service", return_value=svc):
        resp = api_client.get("/api/week?start=2026-03-09")
    assert resp.status_code == 500
    assert "error" in resp.json()


def test_week_conflicts_serialized_as_lists(api_client):
    svc = _mock_service()
    svc.detect_conflicts.return_value = [
        ({"Title": "A", "Time": "09:00"}, {"Title": "B", "Time": "09:00"}),
    ]
    with patch("claude_scheduler.timetable.api.get_service", return_value=svc):
        resp = api_client.get("/api/week?start=2026-03-09")
    assert resp.status_code == 200
    conflicts = resp.json()["conflicts"]
    assert len(conflicts) == 1
    assert isinstance(conflicts[0], list)
    assert len(conflicts[0]) == 2


# --- 3. GET /api/month/{year}/{month} ---

def test_month_returns_weeks(api_client):
    svc = _mock_service()
    with patch("claude_scheduler.timetable.api.get_service", return_value=svc):
        resp = api_client.get("/api/month/2026/3")
    assert resp.status_code == 200
    data = resp.json()
    assert "weeks" in data
    assert len(data["weeks"]) >= 4
    assert data["year"] == 2026
    assert data["month"] == 3
    assert "month_label" in data
    assert "prev_year" in data
    assert "prev_month" in data
    assert "next_year" in data
    assert "next_month" in data
    assert "today" in data


def test_month_prev_next_january(api_client):
    svc = _mock_service()
    with patch("claude_scheduler.timetable.api.get_service", return_value=svc):
        resp = api_client.get("/api/month/2026/1")
    data = resp.json()
    assert data["prev_year"] == 2025
    assert data["prev_month"] == 12
    assert data["next_year"] == 2026
    assert data["next_month"] == 2


def test_month_prev_next_december(api_client):
    svc = _mock_service()
    with patch("claude_scheduler.timetable.api.get_service", return_value=svc):
        resp = api_client.get("/api/month/2026/12")
    data = resp.json()
    assert data["prev_year"] == 2026
    assert data["prev_month"] == 11
    assert data["next_year"] == 2027
    assert data["next_month"] == 1


# --- 4. GET /api/day/{date_str} ---

def test_day_returns_agenda(api_client):
    svc = _mock_service()
    svc.get_daily_agenda.return_value = {"Duc": [], "Family": []}
    with patch("claude_scheduler.timetable.api.get_service", return_value=svc):
        resp = api_client.get("/api/day/2026-03-09")
    assert resp.status_code == 200
    data = resp.json()
    assert "agenda" in data
    assert data["date_str"] == "2026-03-09"
    assert "date_label" in data
    assert "reminders" in data
    assert "conflicts" in data


def test_day_adds_row_index(api_client):
    svc = _mock_service()
    entry = {"Date": "2026-03-09", "Time": "09:00", "Title": "Test", "_type": "Tasks"}
    svc.get_daily_agenda.return_value = {"Duc": [entry]}
    # fetch_sheet returns records that match the entry
    svc.sheets.fetch_sheet.side_effect = lambda sheet: (
        [{"Date": "2026-03-09", "Time": "09:00", "Title": "Test"}] if sheet == "Tasks" else []
    )
    with patch("claude_scheduler.timetable.api.get_service", return_value=svc):
        resp = api_client.get("/api/day/2026-03-09")
    assert resp.status_code == 200
    agenda = resp.json()["agenda"]
    assert agenda["Duc"][0]["_row_index"] == 0


def test_day_with_member_filter(api_client):
    svc = _mock_service()
    svc.get_daily_agenda.return_value = {}
    with patch("claude_scheduler.timetable.api.get_service", return_value=svc):
        resp = api_client.get("/api/day/2026-03-09?member=Wife")
    assert resp.status_code == 200
    svc.get_daily_agenda.assert_called_once_with("2026-03-09", member="Wife")


# --- 5. GET /api/activity ---

def test_activity_returns_log(api_client):
    mock_log = [{"timestamp": "2026-03-09T10:00:00", "action": "add", "sheet": "Tasks", "data": {}}]
    with patch("claude_scheduler.timetable.api.get_activity_log", return_value=mock_log):
        resp = api_client.get("/api/activity")
    assert resp.status_code == 200
    data = resp.json()
    assert "log" in data
    assert len(data["log"]) == 1


def test_activity_empty_log(api_client):
    with patch("claude_scheduler.timetable.api.get_activity_log", return_value=[]):
        resp = api_client.get("/api/activity")
    assert resp.status_code == 200
    assert resp.json()["log"] == []


# --- 6. GET /api/templates ---

def test_templates_returns_list(api_client):
    resp = api_client.get("/api/templates")
    assert resp.status_code == 200
    data = resp.json()
    assert "templates" in data
    assert len(data["templates"]) >= 1
    tpl = data["templates"][0]
    assert "id" in tpl
    assert "name" in tpl
    assert "description" in tpl
    assert "entry_count" in tpl


# --- 7. GET /api/colors ---

def test_colors_returns_current_and_presets(api_client):
    resp = api_client.get("/api/colors")
    assert resp.status_code == 200
    data = resp.json()
    assert "current_colors" in data
    assert "color_presets" in data
    assert "blue" in data["color_presets"]


# --- 8. GET /api/export.ics ---

def test_export_ical_returns_text_calendar(api_client):
    svc = _mock_service()
    svc.get_all_entries_for_range.return_value = [
        {"_type": "Tasks", "Date": "2026-03-09", "Time": "09:00", "Title": "Test task", "Person": "Duc"},
    ]
    with patch("claude_scheduler.timetable.api.get_service", return_value=svc):
        resp = api_client.get("/api/export.ics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/calendar")
    assert "VCALENDAR" in resp.text


def test_export_ical_with_member(api_client):
    svc = _mock_service()
    with patch("claude_scheduler.timetable.api.get_service", return_value=svc):
        resp = api_client.get("/api/export.ics?member=Duc&weeks=2")
    assert resp.status_code == 200
    svc.get_all_entries_for_range.assert_called_once()
    assert svc.get_all_entries_for_range.call_args[1]["member"] == "Duc"


# --- 9. POST /api/entries ---

def test_create_entry_tasks(api_client):
    svc = _mock_service()
    with patch("claude_scheduler.timetable.api.get_service", return_value=svc):
        resp = api_client.post("/api/entries", json={
            "sheet": "Tasks", "date": "2026-03-09", "time": "09:00",
            "person": "Duc", "title": "Test task",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["entry"]["Title"] == "Test task"
    svc.sheets.append_row.assert_called_once()
    call_args = svc.sheets.append_row.call_args
    assert call_args[0][0] == "Tasks"


def test_create_entry_study(api_client):
    svc = _mock_service()
    with patch("claude_scheduler.timetable.api.get_service", return_value=svc):
        resp = api_client.post("/api/entries", json={
            "sheet": "Study", "date": "2026-03-09", "time": "10:00",
            "person": "Child1", "subject": "Math", "topic": "Algebra",
            "entry_type": "class",
        })
    assert resp.status_code == 200
    call_args = svc.sheets.append_row.call_args
    assert call_args[0][0] == "Study"
    assert call_args[0][1]["Subject"] == "Math"


def test_create_entry_events(api_client):
    svc = _mock_service()
    with patch("claude_scheduler.timetable.api.get_service", return_value=svc):
        resp = api_client.post("/api/entries", json={
            "sheet": "Events", "date": "2026-03-09", "time": "14:00",
            "end_time": "16:00", "title": "Party",
            "participants": "Family",
        })
    assert resp.status_code == 200
    call_args = svc.sheets.append_row.call_args
    assert call_args[0][0] == "Events"
    assert call_args[0][1]["Start Time"] == "14:00"


def test_create_entry_reminders(api_client):
    svc = _mock_service()
    with patch("claude_scheduler.timetable.api.get_service", return_value=svc):
        resp = api_client.post("/api/entries", json={
            "sheet": "Reminders", "date": "2026-03-09", "time": "08:00",
            "person": "Wife", "title": "Buy groceries", "priority": "high",
        })
    assert resp.status_code == 200
    call_args = svc.sheets.append_row.call_args
    assert call_args[0][0] == "Reminders"
    assert call_args[0][1]["Priority"] == "high"


# --- 10. PUT /api/entries/{sheet}/{row_index} ---

def test_update_entry(api_client):
    svc = _mock_service()
    with patch("claude_scheduler.timetable.api.get_service", return_value=svc):
        resp = api_client.put("/api/entries/Tasks/3", json={
            "date": "2026-03-09", "time": "10:00",
            "person": "Duc", "title": "Updated task", "status": "done",
        })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    svc.update_entry.assert_called_once_with("Tasks", 3, {
        "Date": "2026-03-09", "Time": "10:00", "Person": "Duc",
        "Title": "Updated task", "Description": "",
        "Status": "done", "Recurring": "",
    })


def test_update_entry_error(api_client):
    svc = _mock_service()
    svc.update_entry.side_effect = Exception("not found")
    with patch("claude_scheduler.timetable.api.get_service", return_value=svc):
        resp = api_client.put("/api/entries/Tasks/99", json={
            "date": "2026-03-09", "title": "fail",
        })
    assert resp.status_code == 500


# --- 11. DELETE /api/entries/{sheet}/{row_index} ---

def test_delete_entry(api_client):
    svc = _mock_service()
    svc.delete_entry.return_value = {"Date": "2026-03-09", "Title": "Deleted"}
    with patch("claude_scheduler.timetable.api.get_service", return_value=svc):
        resp = api_client.delete("/api/entries/Tasks/2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["deleted"]["Title"] == "Deleted"
    svc.delete_entry.assert_called_once_with("Tasks", 2)


def test_delete_entry_error(api_client):
    svc = _mock_service()
    svc.delete_entry.side_effect = Exception("row out of range")
    with patch("claude_scheduler.timetable.api.get_service", return_value=svc):
        resp = api_client.delete("/api/entries/Tasks/99")
    assert resp.status_code == 500


# --- 12. POST /api/toggle/{sheet}/{row_index} ---

def test_toggle_task(api_client):
    svc = _mock_service()
    svc.toggle_task_status.return_value = "done"
    with patch("claude_scheduler.timetable.api.get_service", return_value=svc):
        resp = api_client.post("/api/toggle/Tasks/5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["new_status"] == "done"


def test_toggle_reminder(api_client):
    svc = _mock_service()
    svc.toggle_reminder_done.return_value = "yes"
    with patch("claude_scheduler.timetable.api.get_service", return_value=svc):
        resp = api_client.post("/api/toggle/Reminders/2")
    assert resp.status_code == 200
    assert resp.json()["new_status"] == "yes"


def test_toggle_invalid_sheet(api_client):
    svc = _mock_service()
    with patch("claude_scheduler.timetable.api.get_service", return_value=svc):
        resp = api_client.post("/api/toggle/Events/1")
    assert resp.status_code == 400
    assert "error" in resp.json()


# --- 13. POST /api/templates/apply ---

def test_apply_template(api_client):
    svc = _mock_service()
    with patch("claude_scheduler.timetable.api.get_service", return_value=svc):
        resp = api_client.post("/api/templates/apply", json={
            "template_id": "school_week",
            "person": "Child1",
            "start_date": "2026-03-09",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["count"] > 0
    assert svc.sheets.append_row.call_count == data["count"]


def test_apply_template_unknown_id(api_client):
    svc = _mock_service()
    with patch("claude_scheduler.timetable.api.get_service", return_value=svc):
        resp = api_client.post("/api/templates/apply", json={
            "template_id": "nonexistent",
            "person": "Child1",
            "start_date": "2026-03-09",
        })
    assert resp.status_code == 200
    assert resp.json()["count"] == 0
