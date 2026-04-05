"""Tools Hub — FastAPI application."""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

app = FastAPI(title="Tools Hub")

SERVER_DIR = Path(__file__).parent
REPO_ROOT = SERVER_DIR.parent
templates = Jinja2Templates(directory=str(SERVER_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(SERVER_DIR / "static")), name="static")

# Registry of installed apps
APPS = []

def register_app(name: str, description: str, prefix: str, icon: str = "🔧"):
    APPS.append({"name": name, "description": description, "prefix": prefix, "icon": icon})

# Register apps
from apps.scheduler.routes import router as scheduler_router
register_app("Scheduler", "Claude task scheduler dashboard", "/scheduler", "📋")
app.include_router(scheduler_router, prefix="/scheduler")

from apps.local_kb.routes import router as kb_router
register_app("Knowledge Base", "Local knowledge base with curated insights", "/kb", "📚")
app.include_router(kb_router, prefix="/kb")

from apps.telegram_bridge.routes import router as tg_router
register_app("Telegram Bridge", "Two-way Telegram bot with plugin system", "/telegram-bridge", "🤖")
app.include_router(tg_router, prefix="/telegram-bridge")

try:
    from apps.dev_workflow.routes import router as workflow_router
    from fastapi.responses import RedirectResponse
    register_app("Dev Workflow", "Dev-to-deploy pipeline dashboard", "/workflow", "🔄")

    # Redirect /workflow → /workflow/ (FastAPI doesn't auto-redirect for router prefixes)
    @app.get("/workflow", include_in_schema=False)
    async def workflow_redirect():
        return RedirectResponse("/workflow/", status_code=307)

    app.include_router(workflow_router, prefix="/workflow")
except Exception as e:
    import traceback
    print(f"[WARN] Failed to load dev_workflow app: {e}")
    traceback.print_exc()


# ── Unified React SPA serving ────────────────────────────────────────────────
# Mount frontend/dist with html=True so Starlette serves index.html for
# directory requests and all static assets. Must be LAST — after all API routers.

_SPA_DIST = REPO_ROOT / "frontend" / "dist"

if _SPA_DIST.exists():
    app.mount("/", StaticFiles(directory=str(_SPA_DIST), html=True), name="spa")
else:
    # No SPA build — fall back to Jinja portal
    @app.get("/", response_class=HTMLResponse)
    async def portal(request: Request):
        return templates.TemplateResponse("portal.html", {"request": request, "apps": APPS})
