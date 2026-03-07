"""Tests for timetable web routes."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client with the timetable router mounted."""
    from claude_scheduler.timetable.routes import router

    app = FastAPI()
    app.include_router(router, prefix="/timetable")

    yield TestClient(app)


def _setup_weekly_mock(mock_svc):
    mock_svc.return_value.get_week_data.return_value = {}
    mock_svc.return_value.get_pending_reminders.return_value = []
    mock_svc.return_value.get_overdue_items.return_value = []
    mock_svc.return_value.detect_conflicts.return_value = []


def _setup_daily_mock(mock_svc):
    mock_svc.return_value.get_daily_agenda.return_value = {}
    mock_svc.return_value.get_pending_reminders.return_value = []
    mock_svc.return_value.detect_conflicts.return_value = []
    mock_svc.return_value.sheets.fetch_sheet.return_value = []


def test_weekly_view_returns_200(client):
    with patch("claude_scheduler.timetable.routes.get_service") as mock_svc:
        _setup_weekly_mock(mock_svc)
        resp = client.get("/timetable/")
    assert resp.status_code == 200


def test_weekly_view_with_week_param(client):
    with patch("claude_scheduler.timetable.routes.get_service") as mock_svc:
        _setup_weekly_mock(mock_svc)
        resp = client.get("/timetable/?week=2026-03-09")
    assert resp.status_code == 200


def test_daily_view_returns_200(client):
    with patch("claude_scheduler.timetable.routes.get_service") as mock_svc:
        _setup_daily_mock(mock_svc)
        resp = client.get("/timetable/day/2026-03-09")
    assert resp.status_code == 200


def test_add_form_returns_200(client):
    resp = client.get("/timetable/add")
    assert resp.status_code == 200


def test_add_form_with_date_param(client):
    resp = client.get("/timetable/add?date_str=2026-03-09&sheet=Study")
    assert resp.status_code == 200


def test_add_entry_redirects(client):
    with patch("claude_scheduler.timetable.routes.get_service") as mock_svc:
        resp = client.post("/timetable/add", data={
            "sheet": "Tasks", "date": "2026-03-09", "time": "09:00",
            "person": "Duc", "title": "Test task",
        }, follow_redirects=False)
    assert resp.status_code == 303
    assert "/timetable/day/2026-03-09" in resp.headers["location"]
    mock_svc.return_value.sheets.append_row.assert_called_once()


def test_add_entry_study_sheet(client):
    with patch("claude_scheduler.timetable.routes.get_service") as mock_svc:
        resp = client.post("/timetable/add", data={
            "sheet": "Study", "date": "2026-03-09", "time": "10:00",
            "person": "Child1", "subject": "Math", "topic": "Algebra",
            "entry_type": "class",
        }, follow_redirects=False)
    assert resp.status_code == 303
    call_args = mock_svc.return_value.sheets.append_row.call_args
    assert call_args[0][0] == "Study"
    assert call_args[0][1]["Subject"] == "Math"


def test_add_entry_events_sheet(client):
    with patch("claude_scheduler.timetable.routes.get_service") as mock_svc:
        resp = client.post("/timetable/add", data={
            "sheet": "Events", "date": "2026-03-09", "time": "14:00",
            "end_time": "16:00", "title": "Birthday party",
            "participants": "Family",
        }, follow_redirects=False)
    assert resp.status_code == 303
    call_args = mock_svc.return_value.sheets.append_row.call_args
    assert call_args[0][0] == "Events"
    assert call_args[0][1]["Start Time"] == "14:00"


def test_get_member_color_known_member():
    from claude_scheduler.timetable.routes import get_member_color, FAMILY_MEMBERS
    color = get_member_color(FAMILY_MEMBERS[0])
    assert "bg" in color
    assert "border" in color
    assert "text" in color


def test_get_member_color_unknown_member():
    from claude_scheduler.timetable.routes import get_member_color
    color = get_member_color("UnknownPerson")
    # Unknown members get a color from the preset cycle (not gray)
    assert "bg" in color
    assert "border" in color
    assert "text" in color
