"""Claude Scheduler — FastAPI web application."""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the background scheduler on app startup."""
    from claude_scheduler.config import get_config
    from claude_scheduler.core.background_scheduler import scheduler_loop

    cfg = get_config()
    task = asyncio.create_task(
        scheduler_loop(cfg.paths.tasks_dir, cfg.paths.logs_dir, cfg.paths.data_dir)
    )
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Claude Scheduler",
    description="Web dashboard for claude-scheduler",
    version="1.0.0",
    lifespan=lifespan,
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

# Knowledge Base
import sys
_tools_dir = Path.home() / "workspace" / "tools"
_hub_dir = _tools_dir / "automation-hub"
sys.path.insert(0, str(_hub_dir))
from apps.local_kb.routes import router as kb_router
register_app("Knowledge Base", "Local knowledge base with curated insights", "/kb", icon="📚")
app.include_router(kb_router, prefix="/kb")

# Telegram Bridge
from apps.telegram_bridge.routes import router as tg_router
register_app("Telegram Bridge", "Two-way Telegram bot with plugin system", "/telegram-bridge", icon="🤖")
app.include_router(tg_router, prefix="/telegram-bridge")

# Dev Workflow
try:
    from apps.dev_workflow.routes import router as workflow_router
    register_app("Dev Workflow", "Dev-to-deploy pipeline dashboard", "/workflow", icon="🔄")
    app.include_router(workflow_router, prefix="/workflow")
except Exception as e:
    print(f"[WARN] Failed to load dev_workflow app: {e}")

# Timetable is a standalone app: run with
# uvicorn claude_scheduler.timetable.app:app --port 7080
