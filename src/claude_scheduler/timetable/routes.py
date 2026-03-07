"""Timetable web routes -- weekly, daily, monthly views, add/edit entries, templates, iCal."""
import calendar
import os
from datetime import date, timedelta
from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response  # noqa: F811
from fastapi.templating import Jinja2Templates
from pathlib import Path

from claude_scheduler.timetable.sheets import SheetsClient, get_activity_log
from claude_scheduler.timetable.service import TimetableService
from claude_scheduler.timetable.i18n import get_translator
from claude_scheduler.timetable.ical import entries_to_ical
from claude_scheduler.timetable.schedule_templates import (
    TEMPLATES, get_template_entries, get_sheet_for_entry,
)

router = APIRouter()

_TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

FAMILY_MEMBERS = [
    m.strip() for m in os.environ.get("FAMILY_MEMBERS", "Duc,Wife,Child1,Child2,Child3").split(",")
]

# Customizable member colors stored in env or defaults
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

# Member color assignments from env: MEMBER_COLORS=Duc:blue,Wife:pink,...
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


def app_context(request: Request, **kwargs):
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

    lang = request.query_params.get("lang", os.environ.get("TIMETABLE_LANG", "vi"))
    t = get_translator(lang)

    return {"request": request, "user": user,
            "family_members": FAMILY_MEMBERS, "t": t, "lang": lang, **kwargs}


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


def deadline_info(entry: dict) -> dict:
    """Calculate deadline status for study entries."""
    deadline = entry.get("Deadline", "")
    if not deadline:
        return {}
    try:
        dl = date.fromisoformat(deadline)
        today = date.today()
        diff = (dl - today).days
        if diff < 0:
            return {"status": "overdue", "days": abs(diff)}
        elif diff == 0:
            return {"status": "due_today", "days": 0}
        else:
            return {"status": "upcoming", "days": diff}
    except ValueError:
        return {}


# --- Weekly View ---
@router.get("/", response_class=HTMLResponse)
async def weekly_view(request: Request, week: str | None = None, member: str = ""):
    today = date.today()
    start = date.fromisoformat(week) if week else today - timedelta(days=today.weekday())
    svc = get_service()
    try:
        week_data = svc.get_week_data(start.isoformat(), member=member)
        reminders = svc.get_pending_reminders()
        overdue = svc.get_overdue_items()
        conflicts_today = svc.detect_conflicts(today.isoformat())
    except Exception as e:
        _reset_service()  # allow retry after fixing config
        from claude_scheduler.timetable.auth import _setup_error_html
        return HTMLResponse(content=_setup_error_html(str(e)))

    days = []
    for i in range(7):
        d = start + timedelta(days=i)
        ds = d.isoformat()
        days.append({
            "date": ds,
            "label": d.strftime("%a %d"),
            "entries": week_data.get(ds, []),
            "is_today": d == today,
        })

    prev_week = (start - timedelta(days=7)).isoformat()
    next_week = (start + timedelta(days=7)).isoformat()

    return templates.TemplateResponse("weekly.html", app_context(
        request, days=days, reminders=reminders, overdue=overdue,
        prev_week=prev_week, next_week=next_week,
        week_label=f"{start.strftime('%b %d')} - {(start + timedelta(days=6)).strftime('%b %d, %Y')}",
        get_member_color=get_member_color,
        selected_member=member,
        conflicts=conflicts_today,
        today_str=today.isoformat(),
    ))


# --- Daily View ---
@router.get("/day/{date_str}", response_class=HTMLResponse)
async def daily_view(request: Request, date_str: str, member: str = ""):
    svc = get_service()
    try:
        agenda = svc.get_daily_agenda(date_str, member=member)
        reminders = svc.get_pending_reminders()
        conflicts = svc.detect_conflicts(date_str)
    except Exception as e:
        _reset_service()
        from claude_scheduler.timetable.auth import _setup_error_html
        return HTMLResponse(content=_setup_error_html(str(e)))
    d = date.fromisoformat(date_str)

    # Add row indices to entries for edit/delete links
    all_records: dict[str, list[dict]] = {}
    for sheet_name in ("Tasks", "Study", "Reminders", "Events"):
        records = svc.sheets.fetch_sheet(sheet_name)
        all_records[sheet_name] = records

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
            entry["_deadline_info"] = deadline_info(entry)

    return templates.TemplateResponse("daily.html", app_context(
        request, agenda=agenda, date_str=date_str,
        date_label=d.strftime("%A, %B %d, %Y"),
        reminders=reminders,
        get_member_color=get_member_color,
        selected_member=member,
        conflicts=conflicts,
    ))


# --- Month View ---
@router.get("/month/{year}/{month}", response_class=HTMLResponse)
async def monthly_view(request: Request, year: int, month: int, member: str = ""):
    svc = get_service()
    try:
        month_data = svc.get_month_data(year, month, member=member)
    except Exception as e:
        _reset_service()
        from claude_scheduler.timetable.auth import _setup_error_html
        return HTMLResponse(content=_setup_error_html(str(e)))

    today = date.today()
    first_day = date(year, month, 1)
    _, days_in_month = calendar.monthrange(year, month)

    # Build calendar weeks (list of 7-day rows)
    # Start from Monday of the week containing the 1st
    start_weekday = first_day.weekday()  # 0=Mon
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

    # Prev/next month
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    month_label = first_day.strftime("%B %Y")

    return templates.TemplateResponse("monthly.html", app_context(
        request, weeks=weeks, year=year, month=month,
        month_label=month_label,
        prev_year=prev_year, prev_month=prev_month,
        next_year=next_year, next_month=next_month,
        get_member_color=get_member_color,
        selected_member=member,
    ))


@router.get("/month", response_class=HTMLResponse)
async def monthly_view_current(request: Request, member: str = ""):
    today = date.today()
    return RedirectResponse(url=f"/month/{today.year}/{today.month}{'?member=' + member if member else ''}", status_code=307)


# --- Add Entry ---
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
    return RedirectResponse(url=f"/day/{entry_date}", status_code=303)


# --- Edit Entry ---
@router.get("/edit/{sheet}/{row_index}", response_class=HTMLResponse)
async def edit_form(request: Request, sheet: str, row_index: int):
    svc = get_service()
    entry = svc.get_entry(sheet, row_index)
    if not entry:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("edit_entry.html", app_context(
        request, sheet=sheet, row_index=row_index, entry=entry,
        sheets=["Tasks", "Study", "Reminders", "Events"],
    ))


@router.post("/edit/{sheet}/{row_index}")
async def save_edit(
    request: Request,
    sheet: str,
    row_index: int,
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
    done: str = Form(""),
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
                      "Description": description, "Priority": priority, "Done": done})
    elif sheet == "Events":
        data.update({"Start Time": time, "End Time": end_time, "Title": title,
                      "Description": description, "Participants": participants})

    svc.update_entry(sheet, row_index, data)
    return RedirectResponse(url=f"/day/{entry_date}", status_code=303)


# --- Delete Entry ---
@router.post("/delete/{sheet}/{row_index}")
async def delete_entry(request: Request, sheet: str, row_index: int):
    svc = get_service()
    deleted = svc.delete_entry(sheet, row_index)
    redirect_date = deleted.get("Date", date.today().isoformat())
    return RedirectResponse(url=f"/timetable/day/{redirect_date}", status_code=303)


# --- Toggle Complete ---
@router.post("/toggle/Tasks/{row_index}")
async def toggle_task(request: Request, row_index: int):
    svc = get_service()
    svc.toggle_task_status(row_index)
    referer = request.headers.get("referer", "/")
    return RedirectResponse(url=referer, status_code=303)


@router.post("/toggle/Reminders/{row_index}")
async def toggle_reminder(request: Request, row_index: int):
    svc = get_service()
    svc.toggle_reminder_done(row_index)
    referer = request.headers.get("referer", "/")
    return RedirectResponse(url=referer, status_code=303)


# --- Activity Log ---
@router.get("/activity", response_class=HTMLResponse)
async def activity_log(request: Request):
    log = get_activity_log(limit=100)
    return templates.TemplateResponse("activity.html", app_context(request, log=log))


# --- Templates ---
@router.get("/templates", response_class=HTMLResponse)
async def templates_page(request: Request):
    lang = request.query_params.get("lang", os.environ.get("TIMETABLE_LANG", "vi"))
    template_list = []
    for tid, tpl in TEMPLATES.items():
        template_list.append({
            "id": tid,
            "name": tpl.get(f"name_{lang}", tpl["name"]),
            "description": tpl.get(f"description_{lang}", tpl["description"]),
            "entry_count": len(tpl["entries"]),
        })
    return templates.TemplateResponse("templates.html", app_context(
        request, template_list=template_list,
    ))


@router.post("/apply-template")
async def apply_template(
    request: Request,
    template_id: str = Form(...),
    person: str = Form(...),
    start_date: str = Form(...),
):
    svc = get_service()
    entries = get_template_entries(template_id, person, start_date)
    for entry in entries:
        sheet = get_sheet_for_entry(entry)
        svc.sheets.append_row(sheet, entry)
    return RedirectResponse(url=f"/?week={start_date}", status_code=303)


# --- Recurring Generation ---
@router.post("/generate-recurring")
async def generate_recurring(request: Request, weeks: int = Form(1)):
    svc = get_service()
    count = svc.generate_recurring(date.today().isoformat(), weeks=weeks)
    return RedirectResponse(url="/", status_code=303)


# --- iCal Export ---
@router.get("/export.ics")
async def export_ical(request: Request, member: str = "", weeks: int = 4):
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


# --- Color Settings ---
@router.get("/colors", response_class=HTMLResponse)
async def color_settings(request: Request):
    current_colors = {}
    for member in FAMILY_MEMBERS:
        color_name = MEMBER_COLOR_MAP.get(member, DEFAULT_COLOR_ORDER[FAMILY_MEMBERS.index(member) % len(DEFAULT_COLOR_ORDER)])
        current_colors[member] = color_name
    return templates.TemplateResponse("colors.html", app_context(
        request, current_colors=current_colors,
        color_presets=COLOR_PRESETS,
    ))
