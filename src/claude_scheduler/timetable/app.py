"""Standalone Family Timetable SPA."""
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
from fastapi.responses import FileResponse, HTMLResponse
from starlette.middleware.sessions import SessionMiddleware

from claude_scheduler.timetable.api import api_router
from claude_scheduler.timetable.auth import auth_router, require_auth

app = FastAPI(title="Family Timetable", version="2.0.0")

TIMETABLE_DIR = Path(__file__).parent
INDEX_HTML = TIMETABLE_DIR / "static" / "index.html"

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "dev-secret-change-me"),
)

# Auth middleware
app.middleware("http")(require_auth)
app.include_router(auth_router)
app.include_router(api_router)


@app.get("/", response_class=HTMLResponse)
async def spa_index():
    return FileResponse(INDEX_HTML)
