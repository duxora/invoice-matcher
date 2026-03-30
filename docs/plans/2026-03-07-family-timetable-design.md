# Family Timetable - Design Document

## Goal

A family timetable web app for Duc's family (2 parents, 3 children aged 6-15) with Google Sheets as the data backend, Google OAuth for access control, deployed publicly on Railway.

## Architecture

```
Google Sheets (4 sheets)  <-->  FastAPI App  <-->  Web Dashboard
                                     |
                              Google OAuth
                                     |
                              Railway (hosting)
```

- New app plugged into existing Tools Hub via `register_app()`
- Mounted at `/timetable` prefix
- Two-way sync with Google Sheets (read on page load with 60s cache, write on form submit)

## Google Sheets Structure

Single spreadsheet with 4 sheets:

| Sheet | Columns |
|-------|---------|
| **Tasks** | Date, Time, Person, Title, Description, Status, Recurring |
| **Study** | Date, Time, Person, Subject, Topic, Type (class/homework/exam), Deadline |
| **Reminders** | Date, Time, Person, Title, Description, Priority, Done |
| **Events** | Date, Start Time, End Time, Title, Description, Participants |

**Person values:** Duc, Wife-name, Child1-name, Child2-name, Child3-name, Family

## Web Dashboard Pages

1. **Weekly overview** (landing) - calendar grid, color-coded per family member, click day for detail
2. **Daily agenda** - per-person timeline for a selected day
3. **Add/Edit form** - create or modify entries (syncs back to Sheets)
4. **Family member filter** - view one person's schedule or all

## Tech Stack

- **FastAPI** (existing) + new router at `/timetable`
- **gspread** + **google-auth** for Google Sheets API
- **authlib** for Google OAuth 2.0 login
- **HTMX** for interactive UI (consistent with scheduler app)
- **Jinja2 templates** with existing dark theme
- **Railway** for deployment

## Authentication Flow

1. User visits `/timetable` -> redirected to Google OAuth consent
2. Google returns auth token -> app verifies email is in allowed list
3. Session cookie set -> user sees dashboard
4. Allowed emails configured via `ALLOWED_EMAILS` environment variable

## Two-Way Sync Strategy

- **Read:** Fetch sheet data on page load, cache for 60 seconds
- **Write:** Form submissions append/update rows via Sheets API
- No real-time sync needed - refresh to see external changes

## Reminders

- On-screen only (highlighted overdue/upcoming items on dashboard)
- No push notifications in v1

## Data Features

### For Parents
- Tasks/chores with status tracking
- Appointments
- Reminders with priority levels

### For Children
- Class/subject schedules
- Homework assignments with deadlines
- Extracurricular activities
- Daily routines

### Shared
- Family events (dinners, outings, vacations)

## Deployment

- Railway with GitHub auto-deploy
- Environment variables for Google credentials and allowed emails
- Single Dockerfile for the FastAPI app
