"""Tools Hub — FastAPI application."""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

app = FastAPI(title="Tools Hub")

SERVER_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(SERVER_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(SERVER_DIR / "static")), name="static")

# Registry of installed apps
APPS = []

def register_app(name: str, description: str, prefix: str, icon: str = "🔧"):
    APPS.append({"name": name, "description": description, "prefix": prefix, "icon": icon})

@app.get("/", response_class=HTMLResponse)
async def portal(request: Request):
    return templates.TemplateResponse("portal.html", {"request": request, "apps": APPS})

# Register apps
from apps.scheduler.routes import router as scheduler_router
register_app("Scheduler", "Claude task scheduler dashboard", "/scheduler", "📋")
app.include_router(scheduler_router, prefix="/scheduler")
