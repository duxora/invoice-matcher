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
