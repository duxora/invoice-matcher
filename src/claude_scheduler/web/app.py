"""Claude Scheduler — FastAPI web application."""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

app = FastAPI(
    title="Claude Scheduler",
    description="Web dashboard for claude-scheduler",
    version="1.0.0",
)

WEB_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")

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

@app.exception_handler(500)
async def server_error(request: Request, exc):
    return templates.TemplateResponse("error.html", {
        "request": request, "apps": APPS,
        "code": 500, "title": "Server Error",
        "message": "Something went wrong. Check the logs for details.",
    }, status_code=500)

# Register apps
from claude_scheduler.web.routes import router as scheduler_router
register_app("Scheduler", "Claude task scheduler dashboard", "/scheduler")
app.include_router(scheduler_router, prefix="/scheduler")
