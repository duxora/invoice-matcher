# Family Timetable — SPA Conversion + Fly.io Deployment

**Date:** 2026-03-07
**Status:** Approved

## Summary

Convert the Family Timetable from server-rendered Jinja2/HTMX to a single-page app using Alpine.js + Tailwind CSS (no build step). Deploy to Fly.io free tier.

## Architecture

- **Backend:** FastAPI JSON API (`/api/*` endpoints). All existing service/sheets logic unchanged.
- **Frontend:** Single `index.html` served at `/`. Alpine.js for reactivity + view switching. Tailwind via CDN.
- **No build step.** No node_modules. No bundler.
- **Auth:** Google OAuth routes stay server-side (`/auth/*`).

## API Endpoints

| Endpoint | Method | Returns |
|----------|--------|---------|
| `/api/week?start=&member=` | GET | `{days, reminders, overdue, conflicts}` |
| `/api/month/{year}/{month}?member=` | GET | `{weeks, month_label}` |
| `/api/day/{date}?member=` | GET | `{agenda, reminders, conflicts}` |
| `/api/entries` | POST | Create entry |
| `/api/entries/{sheet}/{row}` | PUT | Update entry |
| `/api/entries/{sheet}/{row}` | DELETE | Delete entry |
| `/api/toggle/{sheet}/{row}` | POST | Toggle done status |
| `/api/templates` | GET | List templates |
| `/api/templates/apply` | POST | Apply template |
| `/api/activity` | GET | Activity log |
| `/api/export.ics?member=` | GET | iCal file download |
| `/api/config` | GET | `{family_members, colors, lang}` |
| `/` | GET | Serves index.html (SPA) |

## Frontend Components

Single `index.html` with Alpine.js `x-data="app()"`:

- **App shell:** sidebar, mobile nav, view state management, shared config
- **Views** (switched via `x-if`): WeekView, MonthView, DayView, AddForm, EditForm, TemplatesView, ActivityView, ColorsView
- **Interactions:** All via `fetch()` — no page reloads. Toggle done in-place, add/edit returns to previous view.

Estimated size: ~400-500 lines HTML.

## Deployment (Fly.io)

- **Dockerfile:** Python 3.12 slim, gunicorn + uvicorn workers, port 8080
- **Secrets:** `GOOGLE_CREDENTIALS_JSON` (base64), `TIMETABLE_SPREADSHEET_ID`, `SESSION_SECRET`, OAuth keys via `fly secrets set`
- **Credentials:** Read `GOOGLE_CREDENTIALS_JSON` env var (base64) → write to temp file at startup. Fallback to file path for local dev.
- **HTTPS:** Auto via `*.fly.dev`
- **Health check:** `GET /api/config`
- **Resources:** Single machine, 256MB RAM (free tier)
