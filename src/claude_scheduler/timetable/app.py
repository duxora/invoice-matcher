"""Standalone Family Timetable web application."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from ~/.config/claude-scheduler/
_config_env = Path.home() / ".config" / "claude-scheduler" / ".env"
if _config_env.exists():
    load_dotenv(_config_env)
else:
    load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import FileSystemLoader
from starlette.middleware.sessions import SessionMiddleware

from claude_scheduler.timetable.routes import router as timetable_router
from claude_scheduler.timetable.auth import auth_router, require_auth

app = FastAPI(
    title="Family Timetable",
    description="Family timetable & study planner",
    version="1.0.0",
)

TIMETABLE_DIR = Path(__file__).parent
TEMPLATES_DIR = TIMETABLE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Static files (Tailwind loaded via CDN, but mount for any future local assets)
_static_dir = TIMETABLE_DIR / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "dev-secret-change-me"),
)

# Auth middleware
app.middleware("http")(require_auth)
app.include_router(auth_router)

# Mount timetable routes at root (standalone app, no /timetable prefix)
app.include_router(timetable_router)


@app.exception_handler(404)
async def not_found(request: Request, exc):
    return HTMLResponse(
        content="<h1>Not Found</h1><a href='/'>Back to Timetable</a>",
        status_code=404,
    )
