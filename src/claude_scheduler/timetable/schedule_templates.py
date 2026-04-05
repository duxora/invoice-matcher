"""Pre-defined schedule templates for Family Timetable."""
from datetime import date, timedelta

TEMPLATES = {
    "school_week": {
        "name": "School Week",
        "name_vi": "Tuan hoc",
        "description": "Mon-Fri class schedule with homework time",
        "description_vi": "Lich hoc tu Thu 2 den Thu 6 voi gio lam bai tap",
        "entries": [
            # Monday
            {"day": 0, "time": "07:30", "subject": "Math", "topic": "Morning class", "type": "class"},
            {"day": 0, "time": "09:00", "subject": "Vietnamese", "topic": "Reading", "type": "class"},
            {"day": 0, "time": "14:00", "subject": "Science", "topic": "Afternoon class", "type": "class"},
            {"day": 0, "time": "17:00", "subject": "Homework", "topic": "Daily homework", "type": "homework"},
            # Tuesday
            {"day": 1, "time": "07:30", "subject": "Vietnamese", "topic": "Writing", "type": "class"},
            {"day": 1, "time": "09:00", "subject": "English", "topic": "Vocabulary", "type": "class"},
            {"day": 1, "time": "14:00", "subject": "Art", "topic": "Drawing", "type": "class"},
            {"day": 1, "time": "17:00", "subject": "Homework", "topic": "Daily homework", "type": "homework"},
            # Wednesday
            {"day": 2, "time": "07:30", "subject": "Math", "topic": "Practice", "type": "class"},
            {"day": 2, "time": "09:00", "subject": "History", "topic": "Lesson", "type": "class"},
            {"day": 2, "time": "14:00", "subject": "P.E.", "topic": "Sports", "type": "class"},
            {"day": 2, "time": "17:00", "subject": "Homework", "topic": "Daily homework", "type": "homework"},
            # Thursday
            {"day": 3, "time": "07:30", "subject": "Science", "topic": "Lab", "type": "class"},
            {"day": 3, "time": "09:00", "subject": "Vietnamese", "topic": "Grammar", "type": "class"},
            {"day": 3, "time": "14:00", "subject": "Music", "topic": "Practice", "type": "class"},
            {"day": 3, "time": "17:00", "subject": "Homework", "topic": "Daily homework", "type": "homework"},
            # Friday
            {"day": 4, "time": "07:30", "subject": "English", "topic": "Conversation", "type": "class"},
            {"day": 4, "time": "09:00", "subject": "Math", "topic": "Review", "type": "class"},
            {"day": 4, "time": "14:00", "subject": "Geography", "topic": "Lesson", "type": "class"},
            {"day": 4, "time": "16:00", "subject": "Homework", "topic": "Weekend homework", "type": "homework"},
        ],
    },
    "daily_routine": {
        "name": "Daily Routine",
        "name_vi": "Lich sinh hoat hang ngay",
        "description": "Standard daily chores and routines for children",
        "description_vi": "Lich sinh hoat hang ngay cho tre",
        "entries": [
            {"day": -1, "time": "06:30", "title": "Wake up & brush teeth", "status": "pending"},
            {"day": -1, "time": "07:00", "title": "Breakfast", "status": "pending"},
            {"day": -1, "time": "12:00", "title": "Lunch", "status": "pending"},
            {"day": -1, "time": "17:30", "title": "Shower", "status": "pending"},
            {"day": -1, "time": "18:00", "title": "Dinner", "status": "pending"},
            {"day": -1, "time": "19:00", "title": "Free time / Reading", "status": "pending"},
            {"day": -1, "time": "21:00", "title": "Bedtime", "status": "pending"},
        ],
    },
    "weekend_family": {
        "name": "Weekend Family",
        "name_vi": "Cuoi tuan gia dinh",
        "description": "Saturday & Sunday family activities",
        "description_vi": "Hoat dong gia dinh cuoi tuan",
        "entries": [
            # Saturday
            {"day": 5, "time": "08:00", "title": "Family breakfast", "participants": "Family"},
            {"day": 5, "time": "09:00", "title": "House cleaning", "participants": "Family"},
            {"day": 5, "time": "10:30", "title": "Grocery shopping", "participants": "Family"},
            {"day": 5, "time": "15:00", "title": "Park / Outdoor activity", "participants": "Family"},
            # Sunday
            {"day": 6, "time": "08:30", "title": "Family brunch", "participants": "Family"},
            {"day": 6, "time": "10:00", "title": "Free time", "participants": "Family"},
            {"day": 6, "time": "16:00", "title": "Prepare for school week", "participants": "Family"},
        ],
    },
}


def get_template_entries(template_id: str, person: str, start_date: str) -> list[dict]:
    """Generate entries from a template for a specific person and start date.

    Args:
        template_id: Key in TEMPLATES dict
        person: Family member name
        start_date: Monday of the target week (ISO format)

    Returns:
        List of dicts ready for sheets.append_row()
    """
    template = TEMPLATES.get(template_id)
    if not template:
        return []

    start = date.fromisoformat(start_date)
    # Align to Monday
    start = start - timedelta(days=start.weekday())

    results = []
    for entry in template["entries"]:
        day_offset = entry["day"]

        if "subject" in entry:
            # Study entry
            if day_offset == -1:
                # daily routine entries applied to all 7 days
                for i in range(7):
                    d = start + timedelta(days=i)
                    results.append({
                        "Date": d.isoformat(),
                        "Time": entry["time"],
                        "Person": person,
                        "Subject": entry["subject"],
                        "Topic": entry.get("topic", ""),
                        "Type": entry.get("type", "class"),
                        "Deadline": "",
                    })
            else:
                d = start + timedelta(days=day_offset)
                results.append({
                    "Date": d.isoformat(),
                    "Time": entry["time"],
                    "Person": person,
                    "Subject": entry["subject"],
                    "Topic": entry.get("topic", ""),
                    "Type": entry.get("type", "class"),
                    "Deadline": "",
                })
        elif "participants" in entry:
            # Event entry
            d = start + timedelta(days=day_offset)
            results.append({
                "Date": d.isoformat(),
                "Start Time": entry["time"],
                "End Time": "",
                "Title": entry["title"],
                "Description": "",
                "Participants": entry.get("participants", person),
            })
        else:
            # Task entry
            if day_offset == -1:
                for i in range(7):
                    d = start + timedelta(days=i)
                    results.append({
                        "Date": d.isoformat(),
                        "Time": entry["time"],
                        "Person": person,
                        "Title": entry["title"],
                        "Description": "",
                        "Status": entry.get("status", "pending"),
                        "Recurring": "",
                    })
            else:
                d = start + timedelta(days=day_offset)
                results.append({
                    "Date": d.isoformat(),
                    "Time": entry["time"],
                    "Person": person,
                    "Title": entry["title"],
                    "Description": "",
                    "Status": entry.get("status", "pending"),
                    "Recurring": "",
                })

    return results


def get_sheet_for_entry(entry: dict) -> str:
    """Determine which sheet an entry belongs to."""
    if "Subject" in entry:
        return "Study"
    if "Participants" in entry:
        return "Events"
    return "Tasks"
