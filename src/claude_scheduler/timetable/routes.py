"""Timetable web routes -- weekly view, daily view, add/edit entries."""
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
    user = None
    try:
        user = getattr(request.state, "user", None)
    except Exception:
        pass
    if user is None:
        try:
            user = request.session.get("user", None)
        except Exception:
            pass
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
    entry_date: str = Form(..., alias="date"),
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
    data: dict = {"Date": entry_date}

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
    return RedirectResponse(url=f"/timetable/day/{entry_date}", status_code=303)
