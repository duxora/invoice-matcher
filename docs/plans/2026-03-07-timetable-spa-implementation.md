# Family Timetable SPA + Fly.io Deploy — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Convert the Family Timetable from server-rendered Jinja2/HTMX to a single-page app with Alpine.js, then deploy to Fly.io.

**Architecture:** FastAPI backend serves JSON API at `/api/*` and a single `index.html` at `/`. Alpine.js handles view switching, data fetching, and reactivity. Tailwind CSS via CDN. No build step.

**Tech Stack:** FastAPI, Alpine.js, Tailwind CSS CDN, Google Sheets API, Fly.io, Docker, gunicorn

---

### Task 1: JSON API Router — Config + Week

**Files:**
- Create: `src/claude_scheduler/timetable/api.py`
- Test: `tests/test_timetable_api.py`

**Step 1: Write the failing test**

```python
# tests/test_timetable_api.py
"""Tests for timetable JSON API."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import date
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def api_client():
    from claude_scheduler.timetable.api import api_router
    app = FastAPI()
    app.include_router(api_router)
    yield TestClient(app)


def test_config_endpoint(api_client):
    resp = api_client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "family_members" in data
    assert "colors" in data
    assert isinstance(data["family_members"], list)


def test_week_endpoint(api_client):
    with patch("claude_scheduler.timetable.api.get_service") as mock:
        mock.return_value.get_week_data.return_value = {}
        mock.return_value.get_pending_reminders.return_value = []
        mock.return_value.get_overdue_items.return_value = []
        mock.return_value.detect_conflicts.return_value = []
        resp = api_client.get("/api/week")
    assert resp.status_code == 200
    data = resp.json()
    assert "days" in data
    assert "week_label" in data
    assert len(data["days"]) == 7


def test_week_endpoint_with_params(api_client):
    with patch("claude_scheduler.timetable.api.get_service") as mock:
        mock.return_value.get_week_data.return_value = {
            "2026-03-09": [{"Date": "2026-03-09", "Title": "Test", "_type": "Tasks"}]
        }
        mock.return_value.get_pending_reminders.return_value = []
        mock.return_value.get_overdue_items.return_value = []
        mock.return_value.detect_conflicts.return_value = []
        resp = api_client.get("/api/week?start=2026-03-09&member=Duc")
    assert resp.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_timetable_api.py -x -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'claude_scheduler.timetable.api'`

**Step 3: Write minimal implementation**

```python
# src/claude_scheduler/timetable/api.py
"""JSON API for Family Timetable SPA."""
import calendar
import os
from datetime import date, timedelta
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from claude_scheduler.timetable.sheets import SheetsClient, get_activity_log
from claude_scheduler.timetable.service import TimetableService
from claude_scheduler.timetable.i18n import get_translator, TRANSLATIONS

api_router = APIRouter(prefix="/api")

FAMILY_MEMBERS = [
    m.strip() for m in os.environ.get("FAMILY_MEMBERS", "Duc,Wife,Child1,Child2,Child3").split(",")
]

COLOR_PRESETS = {
    "blue": {"bg": "bg-blue-500/20", "border": "border-blue-400", "text": "text-blue-400", "hex": "#60a5fa"},
    "pink": {"bg": "bg-pink-500/20", "border": "border-pink-400", "text": "text-pink-400", "hex": "#f472b6"},
    "green": {"bg": "bg-green-500/20", "border": "border-green-400", "text": "text-green-400", "hex": "#4ade80"},
    "yellow": {"bg": "bg-yellow-500/20", "border": "border-yellow-400", "text": "text-yellow-400", "hex": "#facc15"},
    "purple": {"bg": "bg-purple-500/20", "border": "border-purple-400", "text": "text-purple-400", "hex": "#c084fc"},
    "red": {"bg": "bg-red-500/20", "border": "border-red-400", "text": "text-red-400", "hex": "#f87171"},
    "cyan": {"bg": "bg-cyan-500/20", "border": "border-cyan-400", "text": "text-cyan-400", "hex": "#22d3ee"},
    "orange": {"bg": "bg-orange-500/20", "border": "border-orange-400", "text": "text-orange-400", "hex": "#fb923c"},
}

DEFAULT_COLOR_ORDER = ["blue", "pink", "green", "yellow", "purple", "red", "cyan", "orange"]

_color_config = os.environ.get("MEMBER_COLORS", "")
MEMBER_COLOR_MAP: dict[str, str] = {}
if _color_config:
    for part in _color_config.split(","):
        if ":" in part:
            name, color = part.split(":", 1)
            MEMBER_COLOR_MAP[name.strip()] = color.strip()

_service: TimetableService | None = None

def get_service() -> TimetableService:
    global _service
    if _service is None:
        spreadsheet_id = os.environ.get("TIMETABLE_SPREADSHEET_ID", "")
        credentials_path = os.environ.get("GOOGLE_CREDENTIALS_PATH", "")
        client = SheetsClient(spreadsheet_id=spreadsheet_id, credentials_path=credentials_path)
        _service = TimetableService(client, family_members=FAMILY_MEMBERS)
    return _service

def _reset_service():
    global _service
    _service = None

def get_member_color(person: str) -> dict:
    color_name = MEMBER_COLOR_MAP.get(person)
    if color_name and color_name in COLOR_PRESETS:
        return COLOR_PRESETS[color_name]
    try:
        idx = FAMILY_MEMBERS.index(person)
    except ValueError:
        idx = len(FAMILY_MEMBERS)
    color_key = DEFAULT_COLOR_ORDER[idx % len(DEFAULT_COLOR_ORDER)]
    return COLOR_PRESETS[color_key]

def _error_response(msg: str) -> JSONResponse:
    _reset_service()
    return JSONResponse({"error": str(msg)}, status_code=500)

def _member_colors() -> dict[str, dict]:
    return {m: get_member_color(m) for m in FAMILY_MEMBERS}


@api_router.get("/config")
async def config():
    lang = os.environ.get("TIMETABLE_LANG", "en")
    return {
        "family_members": FAMILY_MEMBERS,
        "colors": _member_colors(),
        "color_presets": COLOR_PRESETS,
        "lang": lang,
        "translations": TRANSLATIONS.get(lang, TRANSLATIONS["en"]),
        "sheets": ["Tasks", "Study", "Reminders", "Events"],
    }


@api_router.get("/week")
async def week(start: str = "", member: str = ""):
    today = date.today()
    start_date = date.fromisoformat(start) if start else today - timedelta(days=today.weekday())
    svc = get_service()
    try:
        week_data = svc.get_week_data(start_date.isoformat(), member=member)
        reminders = svc.get_pending_reminders()
        overdue = svc.get_overdue_items()
        conflicts = svc.detect_conflicts(today.isoformat())
    except Exception as e:
        return _error_response(e)

    days = []
    for i in range(7):
        d = start_date + timedelta(days=i)
        ds = d.isoformat()
        days.append({
            "date": ds,
            "label": d.strftime("%a %d"),
            "entries": week_data.get(ds, []),
            "is_today": d == today,
        })

    return {
        "days": days,
        "reminders": reminders,
        "overdue": overdue,
        "conflicts": [[c[0], c[1]] for c in conflicts],
        "prev_week": (start_date - timedelta(days=7)).isoformat(),
        "next_week": (start_date + timedelta(days=7)).isoformat(),
        "week_label": f"{start_date.strftime('%b %d')} - {(start_date + timedelta(days=6)).strftime('%b %d, %Y')}",
        "today": today.isoformat(),
    }
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_timetable_api.py -x -v`
Expected: 3 tests PASS

**Step 5: Commit**

```bash
git add src/claude_scheduler/timetable/api.py tests/test_timetable_api.py
git commit -m "feat(timetable): add JSON API for config and week endpoints"
```

---

### Task 2: JSON API — Month, Day, Activity, Templates, Colors

**Files:**
- Modify: `src/claude_scheduler/timetable/api.py`
- Modify: `tests/test_timetable_api.py`

**Step 1: Write the failing tests**

Append to `tests/test_timetable_api.py`:

```python
def test_month_endpoint(api_client):
    with patch("claude_scheduler.timetable.api.get_service") as mock:
        mock.return_value.get_month_data.return_value = {}
        resp = api_client.get("/api/month/2026/3")
    assert resp.status_code == 200
    data = resp.json()
    assert "weeks" in data
    assert "month_label" in data


def test_day_endpoint(api_client):
    with patch("claude_scheduler.timetable.api.get_service") as mock:
        mock.return_value.get_daily_agenda.return_value = {"Duc": [], "Wife": []}
        mock.return_value.get_pending_reminders.return_value = []
        mock.return_value.detect_conflicts.return_value = []
        mock.return_value.sheets.fetch_sheet.return_value = []
        resp = api_client.get("/api/day/2026-03-09")
    assert resp.status_code == 200
    data = resp.json()
    assert "agenda" in data
    assert "date_label" in data


def test_activity_endpoint(api_client):
    with patch("claude_scheduler.timetable.api.get_activity_log", return_value=[]):
        resp = api_client.get("/api/activity")
    assert resp.status_code == 200
    assert resp.json() == {"log": []}


def test_templates_endpoint(api_client):
    resp = api_client.get("/api/templates")
    assert resp.status_code == 200
    data = resp.json()
    assert "templates" in data
    assert len(data["templates"]) > 0


def test_colors_endpoint(api_client):
    resp = api_client.get("/api/colors")
    assert resp.status_code == 200
    data = resp.json()
    assert "current_colors" in data
    assert "color_presets" in data
```

**Step 2: Run test to verify they fail**

Run: `python -m pytest tests/test_timetable_api.py -x -v`
Expected: FAIL — missing endpoints

**Step 3: Implement endpoints**

Append to `src/claude_scheduler/timetable/api.py`:

```python
from claude_scheduler.timetable.schedule_templates import TEMPLATES


@api_router.get("/month/{year}/{month}")
async def month(year: int, month: int, member: str = ""):
    svc = get_service()
    try:
        month_data = svc.get_month_data(year, month, member=member)
    except Exception as e:
        return _error_response(e)

    today = date.today()
    first_day = date(year, month, 1)
    _, days_in_month = calendar.monthrange(year, month)
    start_weekday = first_day.weekday()
    cal_start = first_day - timedelta(days=start_weekday)

    weeks = []
    current = cal_start
    while current <= date(year, month, days_in_month) or current.weekday() != 0:
        week = []
        for _ in range(7):
            ds = current.isoformat()
            week.append({
                "date": ds,
                "day": current.day,
                "in_month": current.month == month,
                "is_today": current == today,
                "entries": month_data.get(ds, []),
            })
            current += timedelta(days=1)
        weeks.append(week)
        if current.month != month and current.weekday() == 0:
            break

    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)

    return {
        "weeks": weeks,
        "year": year,
        "month": month,
        "month_label": first_day.strftime("%B %Y"),
        "prev_year": prev_year, "prev_month": prev_month,
        "next_year": next_year, "next_month": next_month,
        "today": today.isoformat(),
    }


@api_router.get("/day/{date_str}")
async def day(date_str: str, member: str = ""):
    svc = get_service()
    try:
        agenda = svc.get_daily_agenda(date_str, member=member)
        reminders = svc.get_pending_reminders()
        conflicts = svc.detect_conflicts(date_str)
    except Exception as e:
        return _error_response(e)

    d = date.fromisoformat(date_str)

    # Add row indices for edit/delete
    all_records: dict[str, list[dict]] = {}
    for sheet_name in ("Tasks", "Study", "Reminders", "Events"):
        all_records[sheet_name] = svc.sheets.fetch_sheet(sheet_name)

    for person, entries in agenda.items():
        for entry in entries:
            sheet = entry.get("_type", "Tasks")
            records = all_records.get(sheet, [])
            for idx, rec in enumerate(records):
                if (rec.get("Date") == entry.get("Date") and
                    rec.get("Time", rec.get("Start Time", "")) == entry.get("Time", entry.get("Start Time", "")) and
                    rec.get("Title", rec.get("Subject", "")) == entry.get("Title", entry.get("Subject", ""))):
                    entry["_row_index"] = idx
                    break

    return {
        "agenda": agenda,
        "date_str": date_str,
        "date_label": d.strftime("%A, %B %d, %Y"),
        "reminders": reminders,
        "conflicts": [[c[0], c[1]] for c in conflicts],
    }


@api_router.get("/activity")
async def activity():
    log = get_activity_log(limit=100)
    return {"log": log}


@api_router.get("/templates")
async def templates_list():
    lang = os.environ.get("TIMETABLE_LANG", "en")
    result = []
    for tid, tpl in TEMPLATES.items():
        result.append({
            "id": tid,
            "name": tpl.get(f"name_{lang}", tpl["name"]),
            "description": tpl.get(f"description_{lang}", tpl["description"]),
            "entry_count": len(tpl["entries"]),
        })
    return {"templates": result}


@api_router.get("/colors")
async def colors():
    current_colors = {}
    for member in FAMILY_MEMBERS:
        try:
            idx = FAMILY_MEMBERS.index(member)
        except ValueError:
            idx = 0
        color_name = MEMBER_COLOR_MAP.get(member, DEFAULT_COLOR_ORDER[idx % len(DEFAULT_COLOR_ORDER)])
        current_colors[member] = color_name
    return {"current_colors": current_colors, "color_presets": COLOR_PRESETS}
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_timetable_api.py -x -v`
Expected: 8 tests PASS

**Step 5: Commit**

```bash
git add src/claude_scheduler/timetable/api.py tests/test_timetable_api.py
git commit -m "feat(timetable): add month, day, activity, templates, colors API endpoints"
```

---

### Task 3: JSON API — CRUD Endpoints (entries, toggle, apply template)

**Files:**
- Modify: `src/claude_scheduler/timetable/api.py`
- Modify: `tests/test_timetable_api.py`

**Step 1: Write the failing tests**

Append to `tests/test_timetable_api.py`:

```python
def test_create_entry(api_client):
    with patch("claude_scheduler.timetable.api.get_service") as mock:
        resp = api_client.post("/api/entries", json={
            "sheet": "Tasks", "date": "2026-03-09", "time": "09:00",
            "person": "Duc", "title": "Test task",
        })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    mock.return_value.sheets.append_row.assert_called_once()


def test_update_entry(api_client):
    with patch("claude_scheduler.timetable.api.get_service") as mock:
        resp = api_client.put("/api/entries/Tasks/0", json={
            "date": "2026-03-09", "time": "10:00", "person": "Duc",
            "title": "Updated",
        })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    mock.return_value.update_entry.assert_called_once()


def test_delete_entry(api_client):
    with patch("claude_scheduler.timetable.api.get_service") as mock:
        mock.return_value.delete_entry.return_value = {"Date": "2026-03-09"}
        resp = api_client.delete("/api/entries/Tasks/0")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_toggle_task(api_client):
    with patch("claude_scheduler.timetable.api.get_service") as mock:
        mock.return_value.toggle_task_status.return_value = "done"
        resp = api_client.post("/api/toggle/Tasks/0")
    assert resp.status_code == 200
    assert resp.json()["new_status"] == "done"


def test_toggle_reminder(api_client):
    with patch("claude_scheduler.timetable.api.get_service") as mock:
        mock.return_value.toggle_reminder_done.return_value = "yes"
        resp = api_client.post("/api/toggle/Reminders/0")
    assert resp.status_code == 200
    assert resp.json()["new_status"] == "yes"


def test_apply_template(api_client):
    with patch("claude_scheduler.timetable.api.get_service") as mock:
        resp = api_client.post("/api/templates/apply", json={
            "template_id": "school_week",
            "person": "Child1",
            "start_date": "2026-03-09",
        })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert resp.json()["count"] > 0
```

**Step 2: Run test to verify they fail**

Run: `python -m pytest tests/test_timetable_api.py -x -v`
Expected: FAIL — endpoints not found (405/404)

**Step 3: Implement CRUD endpoints**

Append to `src/claude_scheduler/timetable/api.py`:

```python
from pydantic import BaseModel
from claude_scheduler.timetable.schedule_templates import get_template_entries, get_sheet_for_entry


class EntryCreate(BaseModel):
    sheet: str
    date: str
    time: str = ""
    person: str = ""
    title: str = ""
    description: str = ""
    subject: str = ""
    topic: str = ""
    entry_type: str = ""
    deadline: str = ""
    priority: str = ""
    end_time: str = ""
    participants: str = ""
    status: str = "pending"
    recurring: str = ""
    done: str = ""


class EntryUpdate(BaseModel):
    date: str
    time: str = ""
    person: str = ""
    title: str = ""
    description: str = ""
    subject: str = ""
    topic: str = ""
    entry_type: str = ""
    deadline: str = ""
    priority: str = ""
    end_time: str = ""
    participants: str = ""
    status: str = "pending"
    recurring: str = ""
    done: str = ""


class TemplateApply(BaseModel):
    template_id: str
    person: str
    start_date: str


def _build_row(sheet: str, body) -> dict:
    data: dict = {"Date": body.date}
    if sheet == "Tasks":
        data.update({"Time": body.time, "Person": body.person, "Title": body.title,
                      "Description": body.description, "Status": body.status, "Recurring": body.recurring})
    elif sheet == "Study":
        data.update({"Time": body.time, "Person": body.person, "Subject": body.subject,
                      "Topic": body.topic, "Type": body.entry_type, "Deadline": body.deadline})
    elif sheet == "Reminders":
        data.update({"Time": body.time, "Person": body.person, "Title": body.title,
                      "Description": body.description, "Priority": body.priority, "Done": body.done})
    elif sheet == "Events":
        data.update({"Start Time": body.time, "End Time": body.end_time, "Title": body.title,
                      "Description": body.description, "Participants": body.participants})
    return data


@api_router.post("/entries")
async def create_entry(body: EntryCreate):
    svc = get_service()
    data = _build_row(body.sheet, body)
    svc.sheets.append_row(body.sheet, data)
    return {"ok": True, "entry": data}


@api_router.put("/entries/{sheet}/{row_index}")
async def update_entry(sheet: str, row_index: int, body: EntryUpdate):
    svc = get_service()
    data = _build_row(sheet, body)
    svc.update_entry(sheet, row_index, data)
    return {"ok": True}


@api_router.delete("/entries/{sheet}/{row_index}")
async def delete_entry(sheet: str, row_index: int):
    svc = get_service()
    deleted = svc.delete_entry(sheet, row_index)
    return {"ok": True, "deleted": deleted}


@api_router.post("/toggle/{sheet}/{row_index}")
async def toggle(sheet: str, row_index: int):
    svc = get_service()
    if sheet == "Tasks":
        new_status = svc.toggle_task_status(row_index)
    elif sheet == "Reminders":
        new_status = svc.toggle_reminder_done(row_index)
    else:
        return JSONResponse({"error": f"Cannot toggle {sheet}"}, status_code=400)
    return {"ok": True, "new_status": new_status}


@api_router.post("/templates/apply")
async def apply_template(body: TemplateApply):
    svc = get_service()
    entries = get_template_entries(body.template_id, body.person, body.start_date)
    for entry in entries:
        sheet = get_sheet_for_entry(entry)
        svc.sheets.append_row(sheet, entry)
    return {"ok": True, "count": len(entries)}
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_timetable_api.py -x -v`
Expected: 14 tests PASS

**Step 5: Commit**

```bash
git add src/claude_scheduler/timetable/api.py tests/test_timetable_api.py
git commit -m "feat(timetable): add CRUD, toggle, and template apply API endpoints"
```

---

### Task 4: iCal Export + SPA Entry Point

**Files:**
- Modify: `src/claude_scheduler/timetable/api.py`
- Modify: `src/claude_scheduler/timetable/app.py`
- Modify: `tests/test_timetable_api.py`

**Step 1: Write the failing tests**

Append to `tests/test_timetable_api.py`:

```python
def test_ical_export(api_client):
    with patch("claude_scheduler.timetable.api.get_service") as mock:
        mock.return_value.get_all_entries_for_range.return_value = [
            {"Date": "2026-03-09", "Time": "09:00", "Title": "Test", "_type": "Tasks"},
        ]
        resp = api_client.get("/api/export.ics")
    assert resp.status_code == 200
    assert "BEGIN:VCALENDAR" in resp.text


def test_spa_serves_html():
    """The root / should serve index.html, not the old Jinja2 weekly view."""
    with patch("claude_scheduler.timetable.auth.AUTH_ENABLED", False):
        from claude_scheduler.timetable.app import app
        client = TestClient(app)
        resp = client.get("/")
    assert resp.status_code == 200
    assert "x-data" in resp.text  # Alpine.js app
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_timetable_api.py::test_ical_export tests/test_timetable_api.py::test_spa_serves_html -x -v`
Expected: FAIL

**Step 3: Add iCal endpoint to api.py**

Append to `src/claude_scheduler/timetable/api.py`:

```python
from fastapi.responses import Response
from claude_scheduler.timetable.ical import entries_to_ical


@api_router.get("/export.ics")
async def export_ical(member: str = "", weeks: int = 4):
    svc = get_service()
    today = date.today()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(weeks=weeks)
    entries = svc.get_all_entries_for_range(start.isoformat(), end.isoformat(), member=member)
    cal_name = f"{member or 'Family'} Timetable"
    ical_str = entries_to_ical(entries, calendar_name=cal_name)
    return Response(
        content=ical_str,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{cal_name}.ics"'},
    )
```

**Step 4: Update app.py to serve SPA**

Replace `src/claude_scheduler/timetable/app.py` contents:

```python
"""Standalone Family Timetable SPA."""
import os
from pathlib import Path
from dotenv import load_dotenv

_config_env = Path.home() / ".config" / "claude-scheduler" / ".env"
if _config_env.exists():
    load_dotenv(_config_env)
else:
    load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from starlette.middleware.sessions import SessionMiddleware

from claude_scheduler.timetable.api import api_router
from claude_scheduler.timetable.auth import auth_router, require_auth

app = FastAPI(title="Family Timetable", version="2.0.0")

TIMETABLE_DIR = Path(__file__).parent
INDEX_HTML = TIMETABLE_DIR / "static" / "index.html"

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "dev-secret-change-me"),
)

app.middleware("http")(require_auth)
app.include_router(auth_router)
app.include_router(api_router)


@app.get("/", response_class=HTMLResponse)
async def spa_index():
    return FileResponse(INDEX_HTML)
```

**Step 5: Create placeholder index.html**

Create `src/claude_scheduler/timetable/static/index.html` with minimal Alpine.js content (placeholder — full SPA built in Task 5):

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Family Timetable</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
</head>
<body class="bg-slate-900 text-slate-200 min-h-screen" x-data="{ loading: true }">
  <div class="flex items-center justify-center min-h-screen">
    <p class="text-slate-400">Loading Family Timetable...</p>
  </div>
</body>
</html>
```

**Step 6: Run tests**

Run: `python -m pytest tests/test_timetable_api.py -x -v`
Expected: 16 tests PASS

**Step 7: Commit**

```bash
git add src/claude_scheduler/timetable/api.py src/claude_scheduler/timetable/app.py \
  src/claude_scheduler/timetable/static/index.html tests/test_timetable_api.py
git commit -m "feat(timetable): add iCal API endpoint and SPA entry point"
```

---

### Task 5: Build the Full SPA (index.html with Alpine.js)

**Files:**
- Rewrite: `src/claude_scheduler/timetable/static/index.html`

This is the largest task. The full SPA in a single HTML file.

**Step 1: Build index.html**

Create `src/claude_scheduler/timetable/static/index.html` with:

1. **Tailwind config** — same dark theme colors as current base.html
2. **Alpine.js app** — `x-data="app()"` with:
   - `view`: current view name (week/month/day/add/edit/templates/activity/colors)
   - `config`: loaded from `/api/config` on init
   - `weekData`, `monthData`, `dayData`: fetched per-view
   - `selectedMember`, `editEntry`, `formData`: shared state
3. **Sidebar** — same as current base.html, click handlers switch `view`
4. **Views** — each wrapped in `<template x-if="view === 'week'">`
5. **Fetch helpers** — `loadWeek()`, `loadMonth()`, `loadDay()`, etc.
6. **Form handling** — `submitEntry()`, `saveEdit()`, `deleteEntry()`, `toggleDone()`

Key patterns:
- `x-init="init()"` — fetch `/api/config` then load default week view
- `@click="view = 'day'; loadDay(date)"` — view switching
- `x-for="day in weekData.days"` — data iteration
- `fetch('/api/entries', {method: 'POST', ...}).then(...)` — mutations

**Reference the current templates** for exact layout/styling:
- `src/claude_scheduler/timetable/templates/base.html` — sidebar structure
- `src/claude_scheduler/timetable/templates/weekly.html` — week grid layout
- `src/claude_scheduler/timetable/templates/monthly.html` — month grid layout
- `src/claude_scheduler/timetable/templates/daily.html` — day view layout
- `src/claude_scheduler/timetable/templates/add_entry.html` — form fields
- `src/claude_scheduler/timetable/templates/edit_entry.html` — edit form

Use `@frontend-design` skill for the final polish.

**Step 2: Manual test in browser**

Run: `uvicorn claude_scheduler.timetable.app:app --port 7080 --reload`

Test each view:
- `/` loads, shows week view
- Click day → day view
- Click month → month view
- Add entry → form, submit, returns to day
- Edit entry → form, submit, returns to day
- Toggle done → updates in place
- Delete → removes entry
- Templates → shows cards, apply works
- Activity → shows log
- Export iCal → downloads .ics file

**Step 3: Commit**

```bash
git add src/claude_scheduler/timetable/static/index.html
git commit -m "feat(timetable): build complete SPA with Alpine.js"
```

---

### Task 6: Dockerfile + gunicorn

**Files:**
- Create: `Dockerfile.timetable`
- Create: `.dockerignore`
- Modify: `pyproject.toml` — add `gunicorn` dependency

**Step 1: Add gunicorn dependency**

In `pyproject.toml`, add `"gunicorn>=22.0.0"` to `dependencies`.

**Step 2: Create Dockerfile**

```dockerfile
# Dockerfile.timetable
FROM python:3.12-slim

WORKDIR /app

# Install deps
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy source
COPY src/ src/

# Google credentials from base64 env var at runtime
COPY <<'EOF' /app/entrypoint.sh
#!/bin/bash
if [ -n "$GOOGLE_CREDENTIALS_JSON" ]; then
  echo "$GOOGLE_CREDENTIALS_JSON" | base64 -d > /tmp/google-credentials.json
  export GOOGLE_CREDENTIALS_PATH=/tmp/google-credentials.json
fi
exec gunicorn claude_scheduler.timetable.app:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8080 \
  --workers 1 \
  --timeout 120
EOF
RUN chmod +x /app/entrypoint.sh

EXPOSE 8080
CMD ["/app/entrypoint.sh"]
```

**Step 3: Create .dockerignore**

```
.git
.claude
__pycache__
*.pyc
tests/
docs/
*.md
.env*
```

**Step 4: Test Docker build locally**

Run: `docker build -f Dockerfile.timetable -t family-timetable .`
Expected: Build succeeds

Run: `docker run -p 8080:8080 -e SESSION_SECRET=test family-timetable`
Expected: Server starts (will error on Sheets connection without creds, but that's OK)

**Step 5: Commit**

```bash
git add Dockerfile.timetable .dockerignore pyproject.toml
git commit -m "feat(timetable): add Dockerfile and gunicorn for production deploy"
```

---

### Task 7: Fly.io Configuration + Deploy

**Files:**
- Create: `fly.timetable.toml`

**Step 1: Install flyctl (if not installed)**

Run: `brew install flyctl` or `curl -L https://fly.io/install.sh | sh`

**Step 2: Create fly.toml**

```toml
# fly.timetable.toml
app = "family-timetable"
primary_region = "sin"  # Singapore, closest to Vietnam

[build]
  dockerfile = "Dockerfile.timetable"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true
  min_machines_running = 0

[[vm]]
  memory = "256mb"
  cpu_kind = "shared"
  cpus = 1

[checks]
  [checks.health]
    type = "http"
    port = 8080
    path = "/api/config"
    interval = "30s"
    timeout = "5s"
```

**Step 3: Launch app**

```bash
fly launch --config fly.timetable.toml --no-deploy
```

**Step 4: Set secrets**

```bash
# Base64 encode the Google credentials JSON file
CREDS_B64=$(base64 < ~/.config/claude-scheduler/google-credentials.json)

fly secrets set \
  GOOGLE_CREDENTIALS_JSON="$CREDS_B64" \
  TIMETABLE_SPREADSHEET_ID="your-spreadsheet-id" \
  SESSION_SECRET="$(openssl rand -hex 32)" \
  TIMETABLE_LANG="en" \
  FAMILY_MEMBERS="Duc,Wife,Child1,Child2,Child3" \
  --config fly.timetable.toml
```

Optional (if using Google OAuth):
```bash
fly secrets set \
  GOOGLE_CLIENT_ID="your-client-id" \
  GOOGLE_CLIENT_SECRET="your-client-secret" \
  --config fly.timetable.toml
```

**Step 5: Deploy**

```bash
fly deploy --config fly.timetable.toml
```

**Step 6: Verify**

```bash
fly status --config fly.timetable.toml
curl https://family-timetable.fly.dev/api/config
```

**Step 7: Commit**

```bash
git add fly.timetable.toml
git commit -m "feat(timetable): add Fly.io deployment config"
```

---

### Task 8: Update SheetsClient for Base64 Credentials

**Files:**
- Modify: `src/claude_scheduler/timetable/sheets.py`
- Modify: `tests/test_timetable_api.py`

**Step 1: Write the failing test**

```python
def test_sheets_client_base64_credentials():
    """SheetsClient should accept GOOGLE_CREDENTIALS_JSON env var."""
    import base64, json, tempfile
    fake_creds = json.dumps({"type": "service_account", "project_id": "test"})
    b64 = base64.b64encode(fake_creds.encode()).decode()
    with patch.dict(os.environ, {"GOOGLE_CREDENTIALS_JSON": b64}):
        from claude_scheduler.timetable.sheets import resolve_credentials_path
        path = resolve_credentials_path("")
        assert path is not None
        assert Path(path).exists()
```

**Step 2: Implement in sheets.py**

Add at module level in `sheets.py`:

```python
import base64
import tempfile

def resolve_credentials_path(path: str) -> str:
    """Resolve credentials: file path or base64 env var."""
    if path and Path(path).exists():
        return path
    b64 = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
    if b64:
        decoded = base64.b64decode(b64)
        tmp = Path(tempfile.gettempdir()) / "google-credentials.json"
        tmp.write_bytes(decoded)
        return str(tmp)
    return path
```

Update `_open_spreadsheet()` to use `resolve_credentials_path(self.credentials_path)`.

**Step 3: Run tests**

Run: `python -m pytest tests/test_timetable_api.py -x -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add src/claude_scheduler/timetable/sheets.py tests/test_timetable_api.py
git commit -m "feat(timetable): support base64 Google credentials for containerized deploy"
```

---

### Task 9: Clean Up — Remove Old Jinja2 Templates

**Files:**
- Delete: `src/claude_scheduler/timetable/templates/*.html` (all 8 Jinja2 templates)
- Delete or archive: `src/claude_scheduler/timetable/routes.py` (old HTML routes)
- Update: `tests/test_timetable_routes.py` — remove or skip (replaced by API tests)
- Update: `tests/test_timetable_e2e.py` — update to test SPA
- Update: `tests/test_timetable_new_features.py` — remove route tests (kept service/i18n/ical/template tests)

**Step 1: Remove old template files**

```bash
rm src/claude_scheduler/timetable/templates/weekly.html
rm src/claude_scheduler/timetable/templates/monthly.html
rm src/claude_scheduler/timetable/templates/daily.html
rm src/claude_scheduler/timetable/templates/add_entry.html
rm src/claude_scheduler/timetable/templates/edit_entry.html
rm src/claude_scheduler/timetable/templates/activity.html
rm src/claude_scheduler/timetable/templates/templates.html
rm src/claude_scheduler/timetable/templates/colors.html
rm src/claude_scheduler/timetable/templates/error_setup.html
rm src/claude_scheduler/timetable/templates/base.html
rm src/claude_scheduler/timetable/routes.py
```

**Step 2: Update e2e test**

```python
# tests/test_timetable_e2e.py
def test_spa_loads():
    with patch("claude_scheduler.timetable.auth.AUTH_ENABLED", False):
        from claude_scheduler.timetable.app import app
        client = TestClient(app)
        resp = client.get("/")
    assert resp.status_code == 200
    assert "x-data" in resp.text
    assert "Family Timetable" in resp.text
```

**Step 3: Remove route-level tests from test_timetable_new_features.py**

Keep: i18n, iCal, templates, service, sheets, deadline_info, month_data tests.
Remove: all `route_client` fixture tests (replaced by API tests in `test_timetable_api.py`).

**Step 4: Run all tests**

Run: `python -m pytest tests/test_timetable*.py -x -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add -A
git commit -m "refactor(timetable): remove Jinja2 templates, use SPA + JSON API only"
```

---

## Summary

| Task | Description | Est. |
|------|-------------|------|
| 1 | API: config + week endpoints | 5 min |
| 2 | API: month, day, activity, templates, colors | 5 min |
| 3 | API: CRUD, toggle, apply template | 5 min |
| 4 | iCal export + SPA entry point | 5 min |
| 5 | Full SPA (index.html with Alpine.js) | 15 min |
| 6 | Dockerfile + gunicorn | 5 min |
| 7 | Fly.io config + deploy | 5 min |
| 8 | Base64 credentials support | 3 min |
| 9 | Clean up old templates | 5 min |
