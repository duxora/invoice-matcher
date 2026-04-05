"""Tests for timetable data service."""
import pytest
from unittest.mock import MagicMock
from datetime import date, timedelta


@pytest.fixture
def mock_sheets():
    client = MagicMock()
    client.fetch_by_date_range.return_value = [
        {"Date": "2026-03-09", "Time": "09:00", "Person": "Duc", "Title": "Meeting"},
        {"Date": "2026-03-10", "Time": "14:00", "Person": "Wife", "Title": "Yoga"},
        {"Date": "2026-03-09", "Time": "10:00", "Person": "Child1", "Subject": "Math", "Topic": "Algebra"},
    ]
    client.fetch_by_date.return_value = [
        {"Date": "2026-03-09", "Time": "09:00", "Person": "Duc", "Title": "Meeting"},
    ]
    return client


def test_get_weekly_data_groups_by_date(mock_sheets):
    from claude_scheduler.timetable.service import TimetableService

    svc = TimetableService(mock_sheets, family_members=["Duc", "Wife", "Child1"])
    week = svc.get_week_data("2026-03-09")

    assert "2026-03-09" in week
    mock_sheets.fetch_by_date_range.assert_called()


def test_get_daily_agenda_groups_by_person(mock_sheets):
    from claude_scheduler.timetable.service import TimetableService

    svc = TimetableService(mock_sheets, family_members=["Duc", "Wife", "Child1"])
    agenda = svc.get_daily_agenda("2026-03-09")

    assert "Duc" in agenda
    mock_sheets.fetch_by_date.assert_called()


def test_get_upcoming_reminders(mock_sheets):
    from claude_scheduler.timetable.service import TimetableService

    mock_sheets.fetch_sheet.return_value = [
        {"Date": "2026-03-09", "Time": "08:00", "Person": "Duc",
         "Title": "Pay bills", "Priority": "high", "Done": ""},
        {"Date": "2026-03-07", "Time": "08:00", "Person": "Duc",
         "Title": "Old reminder", "Priority": "low", "Done": "yes"},
    ]

    svc = TimetableService(mock_sheets, family_members=["Duc"])
    reminders = svc.get_pending_reminders()

    assert len(reminders) == 1
    assert reminders[0]["Title"] == "Pay bills"
