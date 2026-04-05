"""End-to-end smoke tests for timetable SPA."""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with patch("claude_scheduler.timetable.auth.AUTH_ENABLED", False):
        from claude_scheduler.timetable.app import app
        yield TestClient(app)


def test_spa_loads(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "x-data" in resp.text
    assert "Family Timetable" in resp.text


def test_api_config(client):
    resp = client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "family_members" in data
    assert "colors" in data


def test_api_week(client):
    with patch("claude_scheduler.timetable.api.get_service") as mock:
        mock.return_value.get_week_data.return_value = {}
        mock.return_value.get_pending_reminders.return_value = []
        mock.return_value.get_overdue_items.return_value = []
        mock.return_value.detect_conflicts.return_value = []
        resp = client.get("/api/week")
    assert resp.status_code == 200
    assert len(resp.json()["days"]) == 7


def test_api_create_entry(client):
    with patch("claude_scheduler.timetable.api.get_service") as mock:
        resp = client.post("/api/entries", json={
            "sheet": "Tasks", "date": "2026-03-09", "time": "09:00",
            "person": "Duc", "title": "Test",
        })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
