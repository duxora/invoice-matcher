"""iCalendar export for Family Timetable."""
from datetime import date, datetime
from hashlib import md5


def _uid(entry: dict, sheet: str) -> str:
    raw = f"{sheet}-{entry.get('Date','')}-{entry.get('Time','')}-{entry.get('Title', entry.get('Subject',''))}"
    return md5(raw.encode()).hexdigest() + "@family-timetable"


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def entries_to_ical(entries: list[dict], calendar_name: str = "Family Timetable") -> str:
    """Convert a list of timetable entries to iCalendar format."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//FamilyTimetable//EN",
        f"X-WR-CALNAME:{_escape(calendar_name)}",
    ]

    for entry in entries:
        sheet = entry.get("_type", "Tasks")
        date_str = entry.get("Date", "")
        if not date_str:
            continue

        time_str = entry.get("Time", entry.get("Start Time", ""))
        end_time_str = entry.get("End Time", "")
        title = entry.get("Title", entry.get("Subject", "Untitled"))
        desc = entry.get("Description", entry.get("Topic", ""))
        person = entry.get("Person", entry.get("Participants", ""))

        # Parse date/time
        try:
            d = date.fromisoformat(date_str)
        except ValueError:
            continue

        if time_str:
            try:
                parts = time_str.split(":")
                dt_start = datetime(d.year, d.month, d.day, int(parts[0]), int(parts[1]))
                dtstart = dt_start.strftime("%Y%m%dT%H%M%S")
            except (ValueError, IndexError):
                dtstart = d.strftime("%Y%m%d")
        else:
            dtstart = d.strftime("%Y%m%d")

        if end_time_str:
            try:
                parts = end_time_str.split(":")
                dt_end = datetime(d.year, d.month, d.day, int(parts[0]), int(parts[1]))
                dtend = dt_end.strftime("%Y%m%dT%H%M%S")
            except (ValueError, IndexError):
                dtend = ""
        else:
            dtend = ""

        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{_uid(entry, sheet)}")
        lines.append(f"DTSTART:{dtstart}")
        if dtend:
            lines.append(f"DTEND:{dtend}")
        lines.append(f"SUMMARY:{_escape(title)}")
        if desc:
            lines.append(f"DESCRIPTION:{_escape(desc)}")
        if person:
            lines.append(f"X-PERSON:{_escape(person)}")
        lines.append(f"CATEGORIES:{sheet}")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)
