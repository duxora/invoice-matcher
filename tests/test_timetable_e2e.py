"""End-to-end smoke test for timetable app."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with patch("claude_scheduler.timetable.auth.AUTH_ENABLED", False):
        from claude_scheduler.web.app import app
        yield TestClient(app)


def test_portal_shows_timetable_app(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Timetable" in resp.text


def test_timetable_weekly_view(client):
    with patch("claude_scheduler.timetable.routes.get_service") as mock:
        mock.return_value.get_week_data.return_value = {}
        mock.return_value.get_pending_reminders.return_value = []
        resp = client.get("/timetable/")
    assert resp.status_code == 200
    assert "Family Timetable" in resp.text


def test_timetable_daily_view(client):
    with patch("claude_scheduler.timetable.routes.get_service") as mock:
        mock.return_value.get_daily_agenda.return_value = {"Duc": [], "Wife": []}
        mock.return_value.get_pending_reminders.return_value = []
        resp = client.get("/timetable/day/2026-03-09")
    assert resp.status_code == 200


def test_timetable_add_form(client):
    resp = client.get("/timetable/add")
    assert resp.status_code == 200
    assert "Add Entry" in resp.text


def test_full_flow_add_and_redirect(client):
    with patch("claude_scheduler.timetable.routes.get_service") as mock:
        resp = client.post("/timetable/add", data={
            "sheet": "Tasks", "date": "2026-03-09", "time": "09:00",
            "person": "Duc", "title": "Test",
        }, follow_redirects=False)
    assert resp.status_code == 303
    assert "/timetable/day/2026-03-09" in resp.headers["location"]
