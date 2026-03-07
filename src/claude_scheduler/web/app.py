"""Claude Scheduler — FastAPI web application."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from ~/.config/claude-scheduler/, fallback to project root
_config_env = Path.home() / ".config" / "claude-scheduler" / ".env"
if _config_env.exists():
    load_dotenv(_config_env)
else:
    load_dotenv()  # fallback: project root .env

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI(
    title="Claude Scheduler",
    description="Web dashboard for claude-scheduler",
    version="1.0.0",
)

WEB_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SESSION_SECRET", "dev-secret-change-me"))

# Registry of installed apps
APPS = []

def register_app(name: str, description: str, prefix: str, icon: str = ""):
    APPS.append({"name": name, "description": description, "prefix": prefix, "icon": icon})

@app.get("/", response_class=HTMLResponse)
async def portal(request: Request):
    return templates.TemplateResponse("portal.html", {"request": request, "apps": APPS})

@app.exception_handler(404)
async def not_found(request: Request, exc):
    return templates.TemplateResponse("error.html", {
        "request": request, "apps": APPS,
        "code": 404, "title": "Not Found",
        "message": "The page you're looking for doesn't exist.",
    }, status_code=404)

# Catch Python PermissionError (raised by gspread when Sheets access is denied)
@app.exception_handler(PermissionError)
async def permission_error(request: Request, exc):
    from claude_scheduler.timetable.auth import _setup_error_html
    return HTMLResponse(content=_setup_error_html(str(exc)), status_code=200)

@app.exception_handler(500)
async def server_error(request: Request, exc):
    return templates.TemplateResponse("error.html", {
        "request": request, "apps": APPS,
        "code": 500, "title": "Server Error",
        "message": "Something went wrong. Check the logs for details.",
    }, status_code=500)

# Register apps
from claude_scheduler.web.routes import router as scheduler_router
register_app("Scheduler", "Claude task scheduler dashboard", "/scheduler", icon="⚙️")
app.include_router(scheduler_router, prefix="/scheduler")

from claude_scheduler.timetable.routes import router as timetable_router
from claude_scheduler.timetable.auth import auth_router, require_auth
app.include_router(auth_router)
app.middleware("http")(require_auth)
register_app("Timetable", "Family timetable & study planner", "/timetable", icon="📅")
app.include_router(timetable_router, prefix="/timetable")
