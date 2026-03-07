"""JSON API for Family Timetable SPA."""
import calendar
import os
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from claude_scheduler.timetable.sheets import SheetsClient, get_activity_log
from claude_scheduler.timetable.service import TimetableService
from claude_scheduler.timetable.i18n import TRANSLATIONS
from claude_scheduler.timetable.ical import entries_to_ical
from claude_scheduler.timetable.schedule_templates import (
    TEMPLATES, get_template_entries, get_sheet_for_entry,
)

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


def _error_response(msg) -> JSONResponse:
    _reset_service()
    return JSONResponse({"error": str(msg)}, status_code=500)


# --- Pydantic models ---

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


class EntryUpdate(BaseModel):
    date: str = ""
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
    status: str = ""
    recurring: str = ""
    done: str = ""


class TemplateApply(BaseModel):
    template_id: str
    person: str
    start_date: str


def _build_row(sheet: str, body) -> dict:
    """Build a row dict from request body based on sheet type."""
    data: dict = {"Date": body.date if hasattr(body, "date") else getattr(body, "date", "")}

    if sheet == "Tasks":
        data.update({
            "Time": body.time, "Person": body.person, "Title": body.title,
            "Description": body.description, "Status": body.status, "Recurring": body.recurring,
        })
    elif sheet == "Study":
        data.update({
            "Time": body.time, "Person": body.person, "Subject": body.subject,
            "Topic": body.topic, "Type": body.entry_type, "Deadline": body.deadline,
        })
    elif sheet == "Reminders":
        data.update({
            "Time": body.time, "Person": body.person, "Title": body.title,
            "Description": body.description, "Priority": body.priority,
            "Done": getattr(body, "done", ""),
        })
    elif sheet == "Events":
        data.update({
            "Start Time": body.time, "End Time": body.end_time, "Title": body.title,
            "Description": body.description, "Participants": body.participants,
        })
    return data


# --- Read endpoints ---

@api_router.get("/config")
async def api_config():
    lang = os.environ.get("TIMETABLE_LANG", "vi")
    translations = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    return {
        "family_members": FAMILY_MEMBERS,
        "colors": {m: get_member_color(m) for m in FAMILY_MEMBERS},
        "color_presets": COLOR_PRESETS,
        "lang": lang,
        "translations": translations,
        "sheets": ["Tasks", "Study", "Reminders", "Events"],
    }


@api_router.get("/week")
async def api_week(start: str = "", member: str = ""):
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

    prev_week = (start_date - timedelta(days=7)).isoformat()
    next_week = (start_date + timedelta(days=7)).isoformat()
    week_label = f"{start_date.strftime('%b %d')} - {(start_date + timedelta(days=6)).strftime('%b %d, %Y')}"

    return {
        "days": days,
        "reminders": reminders,
        "overdue": overdue,
        "conflicts": [[c[0], c[1]] for c in conflicts],
        "prev_week": prev_week,
        "next_week": next_week,
        "week_label": week_label,
        "today": today.isoformat(),
    }


@api_router.get("/month/{year}/{month}")
async def api_month(year: int, month: int, member: str = ""):
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

    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    month_label = first_day.strftime("%B %Y")

    return {
        "weeks": weeks,
        "year": year,
        "month": month,
        "month_label": month_label,
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
        "today": today.isoformat(),
    }


@api_router.get("/day/{date_str}")
async def api_day(date_str: str, member: str = ""):
    svc = get_service()
    try:
        agenda = svc.get_daily_agenda(date_str, member=member)
        reminders = svc.get_pending_reminders()
        conflicts = svc.detect_conflicts(date_str)
    except Exception as e:
        return _error_response(e)

    d = date.fromisoformat(date_str)

    # Add row indices to entries for edit/delete
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

    return {
        "agenda": agenda,
        "date_str": date_str,
        "date_label": d.strftime("%A, %B %d, %Y"),
        "reminders": reminders,
        "conflicts": [[c[0], c[1]] for c in conflicts],
    }


@api_router.get("/activity")
async def api_activity():
    log = get_activity_log(limit=100)
    return {"log": log}


@api_router.get("/templates")
async def api_templates():
    lang = os.environ.get("TIMETABLE_LANG", "vi")
    template_list = []
    for tid, tpl in TEMPLATES.items():
        template_list.append({
            "id": tid,
            "name": tpl.get(f"name_{lang}", tpl["name"]),
            "description": tpl.get(f"description_{lang}", tpl["description"]),
            "entry_count": len(tpl["entries"]),
        })
    return {"templates": template_list}


@api_router.get("/colors")
async def api_colors():
    current_colors = {}
    for member in FAMILY_MEMBERS:
        color_name = MEMBER_COLOR_MAP.get(
            member,
            DEFAULT_COLOR_ORDER[FAMILY_MEMBERS.index(member) % len(DEFAULT_COLOR_ORDER)],
        )
        current_colors[member] = color_name
    return {
        "current_colors": current_colors,
        "color_presets": COLOR_PRESETS,
    }


@api_router.get("/export.ics")
async def api_export_ical(member: str = "", weeks: int = 4):
    svc = get_service()
    try:
        today = date.today()
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(weeks=weeks)

        entries = svc.get_all_entries_for_range(start.isoformat(), end.isoformat(), member=member)
        cal_name = f"{member or 'Family'} Timetable"
        ical_str = entries_to_ical(entries, calendar_name=cal_name)
    except Exception as e:
        return _error_response(e)

    return Response(
        content=ical_str,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{cal_name}.ics"'},
    )


# --- Mutation endpoints ---

@api_router.post("/entries")
async def api_create_entry(body: EntryCreate):
    svc = get_service()
    try:
        data = _build_row(body.sheet, body)
        svc.sheets.append_row(body.sheet, data)
    except Exception as e:
        return _error_response(e)
    return {"ok": True, "entry": data}


@api_router.put("/entries/{sheet}/{row_index}")
async def api_update_entry(sheet: str, row_index: int, body: EntryUpdate):
    svc = get_service()
    try:
        data = _build_row(sheet, body)
        svc.update_entry(sheet, row_index, data)
    except Exception as e:
        return _error_response(e)
    return {"ok": True}


@api_router.delete("/entries/{sheet}/{row_index}")
async def api_delete_entry(sheet: str, row_index: int):
    svc = get_service()
    try:
        deleted = svc.delete_entry(sheet, row_index)
    except Exception as e:
        return _error_response(e)
    return {"ok": True, "deleted": deleted}


@api_router.post("/toggle/{sheet}/{row_index}")
async def api_toggle(sheet: str, row_index: int):
    svc = get_service()
    try:
        if sheet == "Tasks":
            new_status = svc.toggle_task_status(row_index)
        elif sheet == "Reminders":
            new_status = svc.toggle_reminder_done(row_index)
        else:
            return JSONResponse({"error": f"Cannot toggle {sheet}"}, status_code=400)
    except Exception as e:
        return _error_response(e)
    return {"ok": True, "new_status": new_status}


@api_router.post("/templates/apply")
async def api_apply_template(body: TemplateApply):
    svc = get_service()
    try:
        entries = get_template_entries(body.template_id, body.person, body.start_date)
        for entry in entries:
            sheet = get_sheet_for_entry(entry)
            svc.sheets.append_row(sheet, entry)
    except Exception as e:
        return _error_response(e)
    return {"ok": True, "count": len(entries)}
