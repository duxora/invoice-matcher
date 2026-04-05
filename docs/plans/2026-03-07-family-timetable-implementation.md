# Family Timetable Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a Family Timetable app to the Tools Hub with Google Sheets backend, Google OAuth, and Railway deployment.

**Architecture:** New FastAPI router at `/timetable` plugged into existing Tools Hub via `register_app()`. Google Sheets API (gspread) for two-way data sync. Google OAuth (authlib) for authentication. HTMX + Jinja2 templates matching existing dark theme.

**Tech Stack:** FastAPI, gspread, google-auth, authlib, HTMX, Tailwind CSS, Jinja2, Railway

---

### Task 1: Add Dependencies

**Files:**
- Modify: `pyproject.toml:12-18`

**Step 1: Add new dependencies to pyproject.toml**

```toml
dependencies = [
    "argcomplete>=3.0.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "jinja2>=3.1.0",
    "rich>=13.0.0",
    "textual>=0.50.0",
    "gspread>=6.0.0",
    "google-auth>=2.28.0",
    "google-auth-oauthlib>=1.2.0",
    "authlib>=1.3.0",
    "itsdangerous>=2.1.0",
    "httpx>=0.27.0",
]
```

**Step 2: Install updated dependencies**

Run: `cd /Users/ducduong/workspace/tools && pip install -e ".[dev]"`
Expected: Successfully installed gspread, google-auth, authlib, itsdangerous, httpx

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "feat(timetable): add Google Sheets and OAuth dependencies"
```

---

### Task 2: Google Sheets Client Module

**Files:**
- Create: `src/claude_scheduler/timetable/__init__.py`
- Create: `src/claude_scheduler/timetable/sheets.py`
- Test: `tests/test_timetable_sheets.py`

**Step 1: Create package init**

```python
"""Family Timetable app."""
```

**Step 2: Write the failing test**

```python
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
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/test_timetable_sheets.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 4: Write the implementation**

```python
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
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_timetable_sheets.py -v`
Expected: All 5 tests PASS

**Step 6: Commit**

```bash
git add src/claude_scheduler/timetable/__init__.py src/claude_scheduler/timetable/sheets.py tests/test_timetable_sheets.py
git commit -m "feat(timetable): add Google Sheets client with caching and two-way sync"
```

---

### Task 3: Google OAuth Authentication Middleware

**Files:**
- Create: `src/claude_scheduler/timetable/auth.py`
- Test: `tests/test_timetable_auth.py`

**Step 1: Write the failing test**

```python
"""Tests for Google OAuth middleware."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware


def make_test_app():
    from claude_scheduler.timetable.auth import require_auth, auth_router

    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key="test-secret")
    app.include_router(auth_router)

    @app.get("/protected")
    async def protected(request):
        return {"user": request.state.user}

    app.middleware("http")(require_auth)
    return app


def test_unauthenticated_redirects_to_login():
    app = make_test_app()
    client = TestClient(app, follow_redirects=False)
    resp = client.get("/protected")
    assert resp.status_code == 307
    assert "/auth/login" in resp.headers["location"]


def test_login_redirects_to_google():
    app = make_test_app()
    client = TestClient(app, follow_redirects=False)
    with patch("claude_scheduler.timetable.auth.GOOGLE_CLIENT_ID", "fake-id"):
        resp = client.get("/auth/login")
    assert resp.status_code in (302, 307)


def test_allowed_emails_check():
    from claude_scheduler.timetable.auth import is_email_allowed

    with patch("claude_scheduler.timetable.auth.ALLOWED_EMAILS", {"duc@example.com", "wife@example.com"}):
        assert is_email_allowed("duc@example.com") is True
        assert is_email_allowed("stranger@example.com") is False
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_timetable_auth.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write the implementation**

```python
"""Google OAuth 2.0 authentication for Family Timetable."""
import os

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth

auth_router = APIRouter(prefix="/auth")

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
ALLOWED_EMAILS: set[str] = set(
    e.strip() for e in os.environ.get("ALLOWED_EMAILS", "").split(",") if e.strip()
)
AUTH_ENABLED = bool(GOOGLE_CLIENT_ID)

# Public paths that skip auth
PUBLIC_PATHS = {"/auth/login", "/auth/callback", "/auth/logout", "/static"}

oauth = OAuth()
if AUTH_ENABLED:
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def is_email_allowed(email: str) -> bool:
    if not ALLOWED_EMAILS:
        return True  # no restriction if not configured
    return email in ALLOWED_EMAILS


async def require_auth(request: Request, call_next):
    """Middleware: redirect to login if not authenticated."""
    if not AUTH_ENABLED:
        return await call_next(request)

    path = request.url.path
    if any(path.startswith(p) for p in PUBLIC_PATHS):
        return await call_next(request)

    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/auth/login", status_code=307)

    request.state.user = user
    return await call_next(request)


@auth_router.get("/login")
async def login(request: Request):
    redirect_uri = str(request.url_for("auth_callback"))
    return await oauth.google.authorize_redirect(request, redirect_uri)


@auth_router.get("/callback")
async def auth_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo", {})
    email = userinfo.get("email", "")

    if not is_email_allowed(email):
        return RedirectResponse(url="/auth/login?error=not_allowed")

    request.session["user"] = {
        "email": email,
        "name": userinfo.get("name", email),
        "picture": userinfo.get("picture", ""),
    }
    return RedirectResponse(url="/timetable/")


@auth_router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/auth/login")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_timetable_auth.py -v`
Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add src/claude_scheduler/timetable/auth.py tests/test_timetable_auth.py
git commit -m "feat(timetable): add Google OAuth authentication middleware"
```

---

### Task 4: Timetable Data Service

**Files:**
- Create: `src/claude_scheduler/timetable/service.py`
- Test: `tests/test_timetable_service.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_timetable_service.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write the implementation**

```python
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
        return [
            r for r in records
            if not r.get("Done") and r.get("Done") != "yes"
        ]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_timetable_service.py -v`
Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add src/claude_scheduler/timetable/service.py tests/test_timetable_service.py
git commit -m "feat(timetable): add data service layer for weekly/daily views"
```

---

### Task 5: Timetable Web Routes

**Files:**
- Create: `src/claude_scheduler/timetable/routes.py`
- Test: `tests/test_timetable_routes.py`

**Step 1: Write the failing test**

```python
"""Tests for timetable web routes."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    # Disable auth for route testing
    with patch("claude_scheduler.timetable.auth.AUTH_ENABLED", False):
        from claude_scheduler.web.app import app
        yield TestClient(app)


def test_weekly_view_returns_200(client):
    with patch("claude_scheduler.timetable.routes.get_service") as mock_svc:
        mock_svc.return_value.get_week_data.return_value = {}
        mock_svc.return_value.get_pending_reminders.return_value = []
        resp = client.get("/timetable/")
    assert resp.status_code == 200


def test_daily_view_returns_200(client):
    with patch("claude_scheduler.timetable.routes.get_service") as mock_svc:
        mock_svc.return_value.get_daily_agenda.return_value = {}
        mock_svc.return_value.get_pending_reminders.return_value = []
        resp = client.get("/timetable/day/2026-03-09")
    assert resp.status_code == 200


def test_add_entry_redirects(client):
    with patch("claude_scheduler.timetable.routes.get_service") as mock_svc:
        resp = client.post("/timetable/add", data={
            "sheet": "Tasks", "date": "2026-03-09", "time": "09:00",
            "person": "Duc", "title": "Test task",
        }, follow_redirects=False)
    assert resp.status_code in (302, 303)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_timetable_routes.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write the implementation**

```python
"""Timetable web routes — weekly view, daily view, add/edit entries."""
import os
from datetime import date, timedelta

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jinja2 import ChoiceLoader, FileSystemLoader
from pathlib import Path

from claude_scheduler.timetable.sheets import SheetsClient
from claude_scheduler.timetable.service import TimetableService

router = APIRouter()

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_loader = ChoiceLoader([
    FileSystemLoader(str(_TEMPLATES_DIR)),
    FileSystemLoader(str(Path(__file__).parent.parent / "web" / "templates")),
])
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
templates.env.loader = _loader

FAMILY_MEMBERS = [
    m.strip() for m in os.environ.get("FAMILY_MEMBERS", "Duc,Wife,Child1,Child2,Child3").split(",")
]


def get_service() -> TimetableService:
    spreadsheet_id = os.environ.get("TIMETABLE_SPREADSHEET_ID", "")
    credentials_path = os.environ.get("GOOGLE_CREDENTIALS_PATH", "")
    client = SheetsClient(spreadsheet_id=spreadsheet_id, credentials_path=credentials_path)
    return TimetableService(client, family_members=FAMILY_MEMBERS)


def app_context(request: Request, **kwargs):
    from claude_scheduler.web.app import APPS
    user = getattr(request.state, "user", None) or request.session.get("user")
    return {"request": request, "apps": APPS, "user": user,
            "family_members": FAMILY_MEMBERS, **kwargs}


# --- Color assignments per family member ---
MEMBER_COLORS = {
    0: {"bg": "bg-blue-500/20", "border": "border-blue-400", "text": "text-blue-400"},
    1: {"bg": "bg-pink-500/20", "border": "border-pink-400", "text": "text-pink-400"},
    2: {"bg": "bg-green-500/20", "border": "border-green-400", "text": "text-green-400"},
    3: {"bg": "bg-yellow-500/20", "border": "border-yellow-400", "text": "text-yellow-400"},
    4: {"bg": "bg-purple-500/20", "border": "border-purple-400", "text": "text-purple-400"},
}


def get_member_color(person: str) -> dict:
    try:
        idx = FAMILY_MEMBERS.index(person)
    except ValueError:
        idx = len(FAMILY_MEMBERS)  # "Family" gets a default
    return MEMBER_COLORS.get(idx, {"bg": "bg-gray-500/20", "border": "border-gray-400", "text": "text-gray-400"})


@router.get("/", response_class=HTMLResponse)
async def weekly_view(request: Request, week: str | None = None):
    today = date.today()
    start = date.fromisoformat(week) if week else today - timedelta(days=today.weekday())
    svc = get_service()
    week_data = svc.get_week_data(start.isoformat())
    reminders = svc.get_pending_reminders()

    days = []
    for i in range(7):
        d = start + timedelta(days=i)
        ds = d.isoformat()
        days.append({"date": ds, "label": d.strftime("%a %d"), "entries": week_data.get(ds, [])})

    prev_week = (start - timedelta(days=7)).isoformat()
    next_week = (start + timedelta(days=7)).isoformat()

    return templates.TemplateResponse("weekly.html", app_context(
        request, days=days, reminders=reminders,
        prev_week=prev_week, next_week=next_week,
        week_label=f"{start.strftime('%b %d')} - {(start + timedelta(days=6)).strftime('%b %d, %Y')}",
        get_member_color=get_member_color,
    ))


@router.get("/day/{date_str}", response_class=HTMLResponse)
async def daily_view(request: Request, date_str: str):
    svc = get_service()
    agenda = svc.get_daily_agenda(date_str)
    reminders = svc.get_pending_reminders()
    d = date.fromisoformat(date_str)

    return templates.TemplateResponse("daily.html", app_context(
        request, agenda=agenda, date_str=date_str,
        date_label=d.strftime("%A, %B %d, %Y"),
        reminders=reminders,
        get_member_color=get_member_color,
    ))


@router.get("/add", response_class=HTMLResponse)
async def add_form(request: Request, sheet: str = "Tasks", date_str: str = ""):
    if not date_str:
        date_str = date.today().isoformat()
    return templates.TemplateResponse("add_entry.html", app_context(
        request, sheet=sheet, date_str=date_str,
        sheets=["Tasks", "Study", "Reminders", "Events"],
    ))


@router.post("/add")
async def add_entry(
    request: Request,
    sheet: str = Form(...),
    date: str = Form(..., alias="date"),
    time: str = Form(""),
    person: str = Form(""),
    title: str = Form(""),
    description: str = Form(""),
    subject: str = Form(""),
    topic: str = Form(""),
    entry_type: str = Form(""),
    deadline: str = Form(""),
    priority: str = Form(""),
    end_time: str = Form(""),
    participants: str = Form(""),
    status: str = Form("pending"),
    recurring: str = Form(""),
):
    svc = get_service()
    data: dict = {"Date": date}

    if sheet == "Tasks":
        data.update({"Time": time, "Person": person, "Title": title,
                      "Description": description, "Status": status, "Recurring": recurring})
    elif sheet == "Study":
        data.update({"Time": time, "Person": person, "Subject": subject,
                      "Topic": topic, "Type": entry_type, "Deadline": deadline})
    elif sheet == "Reminders":
        data.update({"Time": time, "Person": person, "Title": title,
                      "Description": description, "Priority": priority, "Done": ""})
    elif sheet == "Events":
        data.update({"Start Time": time, "End Time": end_time, "Title": title,
                      "Description": description, "Participants": participants})

    svc.sheets.append_row(sheet, data)
    return RedirectResponse(url=f"/timetable/day/{date}", status_code=303)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_timetable_routes.py -v`
Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add src/claude_scheduler/timetable/routes.py tests/test_timetable_routes.py
git commit -m "feat(timetable): add web routes for weekly, daily, and add entry views"
```

---

### Task 6: HTML Templates

**Files:**
- Create: `src/claude_scheduler/timetable/templates/weekly.html`
- Create: `src/claude_scheduler/timetable/templates/daily.html`
- Create: `src/claude_scheduler/timetable/templates/add_entry.html`

**Step 1: Create weekly view template**

```html
{% extends "base.html" %}
{% block title %}Family Timetable - Week{% endblock %}

{% block content %}
<div class="mb-6 flex items-center justify-between">
  <div>
    <h1 class="text-2xl font-bold">Family Timetable</h1>
    <p class="text-hub-muted text-sm">{{ week_label }}</p>
  </div>
  <div class="flex items-center gap-3">
    <a href="/timetable/?week={{ prev_week }}" class="btn btn-ghost">&larr; Prev</a>
    <a href="/timetable/" class="btn btn-ghost">Today</a>
    <a href="/timetable/?week={{ next_week }}" class="btn btn-ghost">Next &rarr;</a>
    <a href="/timetable/add" class="btn btn-primary">+ Add</a>
  </div>
</div>

<!-- Pending reminders banner -->
{% if reminders %}
<div class="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3 mb-4">
  <span class="text-yellow-400 text-sm font-medium">{{ reminders|length }} pending reminder(s)</span>
  <span class="text-hub-muted text-xs ml-2">
    {% for r in reminders[:3] %}{{ r.Title }}{% if not loop.last %}, {% endif %}{% endfor %}
    {% if reminders|length > 3 %}...{% endif %}
  </span>
</div>
{% endif %}

<!-- Weekly grid -->
<div class="grid grid-cols-7 gap-2">
  {% for day in days %}
  <div class="bg-hub-card border border-hub-border rounded-lg p-3 min-h-[200px]">
    <a href="/timetable/day/{{ day.date }}"
       class="block text-sm font-medium mb-2 hover:text-hub-accent transition-colors">
      {{ day.label }}
    </a>
    <div class="space-y-1">
      {% for entry in day.entries[:6] %}
      {% set color = get_member_color(entry.get("Person", "Family")) %}
      <div class="{{ color.bg }} {{ color.border }} border-l-2 rounded-r px-2 py-1">
        <div class="text-xs {{ color.text }}">{{ entry.get("Time", entry.get("Start Time", "")) }}</div>
        <div class="text-xs truncate">{{ entry.get("Title", entry.get("Subject", "")) }}</div>
        <div class="text-[10px] text-hub-muted">{{ entry.get("Person", entry.get("Participants", "")) }}</div>
      </div>
      {% endfor %}
      {% if day.entries|length > 6 %}
      <a href="/timetable/day/{{ day.date }}" class="text-[10px] text-hub-accent">+{{ day.entries|length - 6 }} more</a>
      {% endif %}
    </div>
  </div>
  {% endfor %}
</div>

<!-- Legend -->
<div class="mt-4 flex gap-4 text-xs text-hub-muted">
  {% for member in family_members %}
  {% set color = get_member_color(member) %}
  <span class="flex items-center gap-1">
    <span class="w-3 h-3 rounded {{ color.bg }} {{ color.border }} border"></span>
    {{ member }}
  </span>
  {% endfor %}
</div>
{% endblock %}
```

**Step 2: Create daily view template**

```html
{% extends "base.html" %}
{% block title %}{{ date_label }} - Family Timetable{% endblock %}

{% block content %}
<div class="mb-2">
  <a href="/timetable/" class="text-hub-accent text-sm hover:underline">&larr; Back to Week</a>
</div>

<div class="mb-6 flex items-center justify-between">
  <div>
    <h1 class="text-2xl font-bold">{{ date_label }}</h1>
  </div>
  <a href="/timetable/add?date_str={{ date_str }}" class="btn btn-primary">+ Add Entry</a>
</div>

<!-- Per-person agenda -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {% for person, entries in agenda.items() %}
  {% set color = get_member_color(person) %}
  <div class="bg-hub-card border border-hub-border rounded-lg p-4">
    <h2 class="text-lg font-semibold mb-3 {{ color.text }}">{{ person }}</h2>
    {% if entries %}
    <div class="space-y-2">
      {% for entry in entries %}
      <div class="{{ color.bg }} rounded p-2">
        <div class="flex items-center justify-between">
          <span class="text-xs text-hub-muted">{{ entry.get("Time", entry.get("Start Time", "")) }}</span>
          <span class="badge badge-{{ entry.get('_type', '')|lower }}">{{ entry.get("_type", "") }}</span>
        </div>
        <div class="text-sm font-medium mt-1">{{ entry.get("Title", entry.get("Subject", "")) }}</div>
        {% if entry.get("Description") or entry.get("Topic") %}
        <div class="text-xs text-hub-muted mt-1">{{ entry.get("Description", entry.get("Topic", "")) }}</div>
        {% endif %}
        {% if entry.get("Deadline") %}
        <div class="text-xs text-yellow-400 mt-1">Due: {{ entry.Deadline }}</div>
        {% endif %}
      </div>
      {% endfor %}
    </div>
    {% else %}
    <p class="text-sm text-hub-muted italic">No entries</p>
    {% endif %}
  </div>
  {% endfor %}
</div>
{% endblock %}
```

**Step 3: Create add entry form template**

```html
{% extends "base.html" %}
{% block title %}Add Entry - Family Timetable{% endblock %}

{% block content %}
<div class="mb-2">
  <a href="/timetable/" class="text-hub-accent text-sm hover:underline">&larr; Back</a>
</div>

<div class="mb-6">
  <h1 class="text-2xl font-bold">Add Entry</h1>
</div>

<div class="bg-hub-card border border-hub-border rounded-lg p-6 max-w-2xl">
  <form method="post" action="/timetable/add" class="space-y-4" id="add-form">
    <div class="grid grid-cols-2 gap-4">
      <div>
        <label for="sheet" class="block text-sm font-medium mb-1">Type *</label>
        <select id="sheet" name="sheet" onchange="toggleFields()"
                class="w-full px-3 py-2 text-sm bg-hub-bg border border-hub-border rounded focus:outline-none focus:border-hub-accent">
          {% for s in sheets %}
          <option value="{{ s }}" {% if s == sheet %}selected{% endif %}>{{ s }}</option>
          {% endfor %}
        </select>
      </div>
      <div>
        <label for="person" class="block text-sm font-medium mb-1">Person *</label>
        <select id="person" name="person"
                class="w-full px-3 py-2 text-sm bg-hub-bg border border-hub-border rounded focus:outline-none focus:border-hub-accent">
          {% for m in family_members %}
          <option value="{{ m }}">{{ m }}</option>
          {% endfor %}
          <option value="Family">Family (shared)</option>
        </select>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <div>
        <label for="date" class="block text-sm font-medium mb-1">Date *</label>
        <input type="date" id="date" name="date" value="{{ date_str }}" required
               class="w-full px-3 py-2 text-sm bg-hub-bg border border-hub-border rounded focus:outline-none focus:border-hub-accent">
      </div>
      <div>
        <label for="time" class="block text-sm font-medium mb-1">Time</label>
        <input type="time" id="time" name="time"
               class="w-full px-3 py-2 text-sm bg-hub-bg border border-hub-border rounded focus:outline-none focus:border-hub-accent">
      </div>
    </div>

    <!-- Common: Title -->
    <div id="field-title">
      <label for="title" class="block text-sm font-medium mb-1">Title *</label>
      <input type="text" id="title" name="title"
             class="w-full px-3 py-2 text-sm bg-hub-bg border border-hub-border rounded focus:outline-none focus:border-hub-accent">
    </div>

    <div id="field-description">
      <label for="description" class="block text-sm font-medium mb-1">Description</label>
      <textarea id="description" name="description" rows="2"
                class="w-full px-3 py-2 text-sm bg-hub-bg border border-hub-border rounded focus:outline-none focus:border-hub-accent"></textarea>
    </div>

    <!-- Study-specific -->
    <div id="field-study" class="hidden space-y-4">
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label for="subject" class="block text-sm font-medium mb-1">Subject</label>
          <input type="text" id="subject" name="subject"
                 class="w-full px-3 py-2 text-sm bg-hub-bg border border-hub-border rounded focus:outline-none focus:border-hub-accent">
        </div>
        <div>
          <label for="topic" class="block text-sm font-medium mb-1">Topic</label>
          <input type="text" id="topic" name="topic"
                 class="w-full px-3 py-2 text-sm bg-hub-bg border border-hub-border rounded focus:outline-none focus:border-hub-accent">
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label for="entry_type" class="block text-sm font-medium mb-1">Type</label>
          <select id="entry_type" name="entry_type"
                  class="w-full px-3 py-2 text-sm bg-hub-bg border border-hub-border rounded focus:outline-none focus:border-hub-accent">
            <option value="class">Class</option>
            <option value="homework">Homework</option>
            <option value="exam">Exam</option>
          </select>
        </div>
        <div>
          <label for="deadline" class="block text-sm font-medium mb-1">Deadline</label>
          <input type="date" id="deadline" name="deadline"
                 class="w-full px-3 py-2 text-sm bg-hub-bg border border-hub-border rounded focus:outline-none focus:border-hub-accent">
        </div>
      </div>
    </div>

    <!-- Reminder-specific -->
    <div id="field-reminder" class="hidden">
      <label for="priority" class="block text-sm font-medium mb-1">Priority</label>
      <select id="priority" name="priority"
              class="w-full px-3 py-2 text-sm bg-hub-bg border border-hub-border rounded focus:outline-none focus:border-hub-accent">
        <option value="low">Low</option>
        <option value="medium" selected>Medium</option>
        <option value="high">High</option>
      </select>
    </div>

    <!-- Event-specific -->
    <div id="field-event" class="hidden space-y-4">
      <div>
        <label for="end_time" class="block text-sm font-medium mb-1">End Time</label>
        <input type="time" id="end_time" name="end_time"
               class="w-full px-3 py-2 text-sm bg-hub-bg border border-hub-border rounded focus:outline-none focus:border-hub-accent">
      </div>
      <div>
        <label for="participants" class="block text-sm font-medium mb-1">Participants</label>
        <input type="text" id="participants" name="participants" placeholder="e.g. Family"
               class="w-full px-3 py-2 text-sm bg-hub-bg border border-hub-border rounded focus:outline-none focus:border-hub-accent">
      </div>
    </div>

    <!-- Tasks-specific -->
    <div id="field-tasks" class="hidden">
      <label for="recurring" class="block text-sm font-medium mb-1">Recurring</label>
      <select id="recurring" name="recurring"
              class="w-full px-3 py-2 text-sm bg-hub-bg border border-hub-border rounded focus:outline-none focus:border-hub-accent">
        <option value="">None</option>
        <option value="daily">Daily</option>
        <option value="weekly">Weekly</option>
        <option value="monthly">Monthly</option>
      </select>
    </div>

    <div class="flex items-center gap-3 pt-2">
      <button type="submit" class="btn btn-primary px-6 py-2">Add Entry</button>
      <a href="/timetable/" class="btn btn-ghost">Cancel</a>
    </div>
  </form>
</div>

<script>
function toggleFields() {
  const sheet = document.getElementById('sheet').value;
  document.getElementById('field-study').classList.toggle('hidden', sheet !== 'Study');
  document.getElementById('field-reminder').classList.toggle('hidden', sheet !== 'Reminders');
  document.getElementById('field-event').classList.toggle('hidden', sheet !== 'Events');
  document.getElementById('field-tasks').classList.toggle('hidden', sheet !== 'Tasks');
  // Hide title for Study (uses Subject instead)
  document.getElementById('field-title').classList.toggle('hidden', sheet === 'Study');
}
toggleFields();
</script>
{% endblock %}
```

**Step 4: Verify templates render (manual)**

Run: `cd /Users/ducduong/workspace/tools && python -c "from claude_scheduler.timetable.routes import router; print('Routes loaded OK')"`
Expected: "Routes loaded OK"

**Step 5: Commit**

```bash
git add src/claude_scheduler/timetable/templates/
git commit -m "feat(timetable): add weekly, daily, and add-entry HTML templates"
```

---

### Task 7: Register Timetable App in Tools Hub

**Files:**
- Modify: `src/claude_scheduler/web/app.py:44-47`
- Modify: `src/claude_scheduler/web/templates/base.html:48-71` (add timetable sub-nav)

**Step 1: Add timetable registration to app.py**

Add after line 47 in `src/claude_scheduler/web/app.py`:

```python
from claude_scheduler.timetable.routes import router as timetable_router
from claude_scheduler.timetable.auth import auth_router, require_auth
from starlette.middleware.sessions import SessionMiddleware
import os

app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SESSION_SECRET", "dev-secret-change-me"))
app.include_router(auth_router)
register_app("Timetable", "Family timetable & study planner", "/timetable", icon="📅")
app.include_router(timetable_router, prefix="/timetable")
```

**Step 2: Add timetable sub-navigation in base.html**

After the scheduler sub-nav block (line 71), add:

```html
{% if request.url.path.startswith(app.prefix) and app.prefix == '/timetable' %}
<div class="ml-4 border-l border-hub-border">
  {% set timetable_links = [
    ("Week View", "/timetable/"),
    ("Today", "/timetable/day/" ~ today),
    ("Add Entry", "/timetable/add"),
  ] %}
  {% for label, href in timetable_links %}
  <a href="{{ href }}"
     class="block px-3 py-1.5 text-xs transition-colors
            {% if request.url.path == href %}
              text-hub-accent
            {% else %}
              text-hub-muted hover:text-hub-text
            {% endif %}">
    {{ label }}
  </a>
  {% endfor %}
</div>
{% endif %}
```

**Step 3: Run existing tests to ensure no regressions**

Run: `pytest tests/ -v`
Expected: All existing tests PASS

**Step 4: Commit**

```bash
git add src/claude_scheduler/web/app.py src/claude_scheduler/web/templates/base.html
git commit -m "feat(timetable): register timetable app in Tools Hub with sidebar navigation"
```

---

### Task 8: Add Timetable-Specific CSS

**Files:**
- Modify: `src/claude_scheduler/web/static/css/custom.css`

**Step 1: Add timetable badges and styles**

Append to custom.css:

```css
/* Timetable type badges */
.badge-tasks { background: rgba(56,189,248,0.15); color: #38bdf8; }
.badge-study { background: rgba(168,85,247,0.15); color: #a855f7; }
.badge-reminders { background: rgba(234,179,8,0.15); color: #facc15; }
.badge-events { background: rgba(34,197,94,0.15); color: #4ade80; }
```

**Step 2: Commit**

```bash
git add src/claude_scheduler/web/static/css/custom.css
git commit -m "feat(timetable): add type-specific badge styles"
```

---

### Task 9: Dockerfile and Railway Configuration

**Files:**
- Create: `Dockerfile`
- Create: `railway.toml`
- Create: `.env.example`

**Step 1: Create Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/
COPY README.md .

RUN pip install --no-cache-dir .

EXPOSE 7000

CMD ["uvicorn", "claude_scheduler.web.app:app", "--host", "0.0.0.0", "--port", "7000"]
```

**Step 2: Create railway.toml**

```toml
[build]
builder = "dockerfile"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "uvicorn claude_scheduler.web.app:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/"
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3
```

**Step 3: Create .env.example**

```bash
# Google OAuth (create at https://console.cloud.google.com/apis/credentials)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# Google Sheets service account credentials (JSON file path)
GOOGLE_CREDENTIALS_PATH=/app/credentials.json

# Spreadsheet ID (from the Google Sheets URL)
TIMETABLE_SPREADSHEET_ID=your-spreadsheet-id

# Comma-separated list of allowed Google emails
ALLOWED_EMAILS=you@gmail.com,wife@gmail.com

# Family member names (comma-separated, order determines colors)
FAMILY_MEMBERS=Duc,Wife,Child1,Child2,Child3

# Session encryption key (generate with: python -c "import secrets; print(secrets.token_hex(32))")
SESSION_SECRET=change-me-to-random-string
```

**Step 4: Add credentials.json to .gitignore**

Append to `.gitignore`:

```
credentials.json
.env
```

**Step 5: Build and test Docker image locally**

Run: `cd /Users/ducduong/workspace/tools && docker build -t tools-hub . && echo "Build OK"`
Expected: "Build OK"

**Step 6: Commit**

```bash
git add Dockerfile railway.toml .env.example .gitignore
git commit -m "feat(timetable): add Dockerfile and Railway deployment config"
```

---

### Task 10: Google Sheets Setup Script

**Files:**
- Create: `scripts/setup_sheets.py`

**Step 1: Create setup script that initializes the spreadsheet**

```python
#!/usr/bin/env python3
"""Create and initialize the Family Timetable Google Spreadsheet."""
import sys
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

SHEETS = {
    "Tasks": ["Date", "Time", "Person", "Title", "Description", "Status", "Recurring"],
    "Study": ["Date", "Time", "Person", "Subject", "Topic", "Type", "Deadline"],
    "Reminders": ["Date", "Time", "Person", "Title", "Description", "Priority", "Done"],
    "Events": ["Date", "Start Time", "End Time", "Title", "Description", "Participants"],
}


def main():
    if len(sys.argv) < 2:
        print("Usage: python setup_sheets.py <credentials.json> [share-email]")
        sys.exit(1)

    creds_path = sys.argv[1]
    share_email = sys.argv[2] if len(sys.argv) > 2 else None

    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    gc = gspread.authorize(creds)

    spreadsheet = gc.create("Family Timetable")
    print(f"Created spreadsheet: {spreadsheet.url}")
    print(f"Spreadsheet ID: {spreadsheet.id}")

    # Remove default Sheet1 after creating our sheets
    for sheet_name, columns in SHEETS.items():
        ws = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=len(columns))
        ws.append_row(columns)
        print(f"  Created sheet: {sheet_name}")

    # Remove default sheet
    default = spreadsheet.worksheet("Sheet1")
    spreadsheet.del_worksheet(default)

    if share_email:
        spreadsheet.share(share_email, perm_type="user", role="writer")
        print(f"  Shared with: {share_email}")

    print(f"\nSet TIMETABLE_SPREADSHEET_ID={spreadsheet.id}")


if __name__ == "__main__":
    main()
```

**Step 2: Commit**

```bash
git add scripts/setup_sheets.py
git commit -m "feat(timetable): add Google Sheets initialization script"
```

---

### Task 11: End-to-End Smoke Test

**Files:**
- Test: `tests/test_timetable_e2e.py`

**Step 1: Write integration test**

```python
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
```

**Step 2: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS (existing + new)

**Step 3: Commit**

```bash
git add tests/test_timetable_e2e.py
git commit -m "test(timetable): add end-to-end smoke tests"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Add dependencies | pyproject.toml |
| 2 | Google Sheets client | timetable/sheets.py + tests |
| 3 | Google OAuth middleware | timetable/auth.py + tests |
| 4 | Data service layer | timetable/service.py + tests |
| 5 | Web routes | timetable/routes.py + tests |
| 6 | HTML templates | weekly.html, daily.html, add_entry.html |
| 7 | Register in Tools Hub | app.py, base.html |
| 8 | CSS styles | custom.css |
| 9 | Docker + Railway config | Dockerfile, railway.toml, .env.example |
| 10 | Sheets setup script | scripts/setup_sheets.py |
| 11 | E2E smoke tests | test_timetable_e2e.py |
