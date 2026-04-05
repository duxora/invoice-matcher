"""Local Knowledge Base web routes — stats, browse, search, ingest."""

import subprocess
import sys
from pathlib import Path

import yaml
from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from jinja2 import ChoiceLoader, FileSystemLoader

router = APIRouter()

SERVER_TEMPLATES = Path(__file__).parent.parent.parent / "server" / "templates"
APP_TEMPLATES = Path(__file__).parent / "templates"

_loader = ChoiceLoader([
    FileSystemLoader(str(APP_TEMPLATES)),
    FileSystemLoader(str(SERVER_TEMPLATES)),
])
templates = Jinja2Templates(directory=str(APP_TEMPLATES))
templates.env.loader = _loader

KB_ROOT = Path.home() / "workspace" / "tools" / "local-kb"
SOURCES_PATH = KB_ROOT / "sources.yaml"
sys.path.insert(0, str(KB_ROOT / "src"))


def app_context(request: Request, **kwargs):
    """Build template context with sidebar navigation data."""
    from claude_scheduler.web.app import APPS
    return {"request": request, "apps": APPS, **kwargs}


def _get_db():
    from local_kb.db import get_connection, init_db
    conn = get_connection(KB_ROOT / "kb.db")
    init_db(conn)
    return conn


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    from local_kb.db import browse_entries, get_stats, get_trending
    conn = _get_db()
    stats = get_stats(conn)
    trending = get_trending(conn, days=7, limit=5)
    entries = browse_entries(conn, domain="", sort_by="recent", limit=10) if stats["total_entries"] > 0 else []
    # Get recent across all domains
    recent = conn.execute(
        "SELECT * FROM entries ORDER BY created DESC LIMIT 10"
    ).fetchall()
    from local_kb.db import _row_to_entry
    entries = [_row_to_entry(r) for r in recent]

    return templates.TemplateResponse("dashboard.html", app_context(
        request,
        stats=stats,
        trending=trending,
        entries=entries,
    ))


# ---------------------------------------------------------------------------
# Entry Detail
# ---------------------------------------------------------------------------

@router.get("/entry/{entry_id}", response_class=HTMLResponse)
async def entry_detail(request: Request, entry_id: str):
    from local_kb.db import get_entry
    conn = _get_db()
    entry = get_entry(conn, entry_id)
    if not entry:
        return HTMLResponse("<h1>Entry not found</h1>", status_code=404)
    return templates.TemplateResponse("entry_detail.html", app_context(
        request,
        entry=entry,
    ))


@router.delete("/entry/{entry_id}")
async def delete_entry(entry_id: str):
    conn = _get_db()
    conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    conn.commit()
    # Delete markdown file
    for domain_dir in (KB_ROOT / "knowledge").iterdir():
        md_file = domain_dir / f"{entry_id}.md"
        if md_file.exists():
            md_file.unlink()
            break
    return RedirectResponse("/kb", status_code=303)


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

@router.get("/sources", response_class=HTMLResponse)
async def sources_page(request: Request):
    sources = {}
    if SOURCES_PATH.exists():
        with open(SOURCES_PATH) as f:
            data = yaml.safe_load(f)
            sources = data.get("sources", {})
    return templates.TemplateResponse("sources.html", app_context(
        request,
        sources=sources,
    ))


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------

@router.post("/ingest", response_class=HTMLResponse)
async def ingest_url(url: str = Form(...), domain: str = Form("tech-trends")):
    from local_kb.db import insert_entry, source_exists
    from local_kb.ingest.distiller import distill_content
    from local_kb.ingest.fetcher import fetch_web_page
    from local_kb.models import KBEntry

    conn = _get_db()
    if source_exists(conn, url):
        return HTMLResponse('<p class="text-yellow-400 text-sm">URL already indexed.</p>')

    raw = fetch_web_page(url, domain)
    if not raw:
        return HTMLResponse(f'<p class="text-red-400 text-sm">Failed to fetch: {url}</p>')

    entry = distill_content(raw.content, source_url=url, domain=domain)
    if not entry:
        return HTMLResponse('<p class="text-red-400 text-sm">Content too thin to distill.</p>')

    insert_entry(conn, entry)
    # Save markdown
    knowledge_dir = KB_ROOT / "knowledge" / entry.domain.value
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    (knowledge_dir / f"{entry.id}.md").write_text(entry.to_markdown())

    return HTMLResponse(
        f'<p class="text-green-400 text-sm">✅ Ingested: <strong>{entry.title}</strong> ({entry.id})</p>'
    )


@router.post("/ingest-all", response_class=HTMLResponse)
async def ingest_all():
    try:
        result = subprocess.run(
            [sys.executable, "-m", "local_kb.cli", "ingest-all"],
            capture_output=True, text=True, timeout=300,
            cwd=str(KB_ROOT),
        )
        output = result.stdout + result.stderr
        return HTMLResponse(
            f'<div class="bg-hub-bg rounded p-3"><pre class="text-xs text-hub-muted whitespace-pre-wrap">{output}</pre></div>'
        )
    except subprocess.TimeoutExpired:
        return HTMLResponse('<p class="text-red-400 text-sm">Ingestion timed out after 5 minutes.</p>')


# ---------------------------------------------------------------------------
# HTMX Partials
# ---------------------------------------------------------------------------

@router.get("/partials/search-results", response_class=HTMLResponse)
async def search_results(request: Request, q: str = Query(""), domain: str = Query("")):
    if not q or len(q) < 2:
        return HTMLResponse("")

    from local_kb.db import search_entries
    conn = _get_db()
    entries = search_entries(conn, q, domain=domain or None, limit=10)
    return templates.TemplateResponse("partials/search_results.html", {
        "request": request,
        "entries": entries,
        "query": q,
    })


@router.get("/partials/browse", response_class=HTMLResponse)
async def browse_partial(request: Request, domain: str = Query("")):
    if not domain:
        return HTMLResponse("")

    from local_kb.db import browse_entries
    conn = _get_db()
    entries = browse_entries(conn, domain, limit=10)
    return templates.TemplateResponse("partials/browse_results.html", {
        "request": request,
        "entries": entries,
    })


@router.get("/partials/trending", response_class=HTMLResponse)
async def trending_partial(request: Request):
    from local_kb.db import get_trending
    conn = _get_db()
    trending = get_trending(conn, days=7, limit=5)
    return templates.TemplateResponse("partials/trending.html", {
        "request": request,
        "trending": trending,
    })


@router.get("/partials/recent", response_class=HTMLResponse)
async def recent_partial(request: Request):
    from local_kb.db import _row_to_entry
    conn = _get_db()
    recent = conn.execute(
        "SELECT * FROM entries ORDER BY created DESC LIMIT 10"
    ).fetchall()
    entries = [_row_to_entry(r) for r in recent]
    return templates.TemplateResponse("partials/entries_table.html", {
        "request": request,
        "entries": entries,
    })


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@router.get("/api/search")
async def api_search(q: str = Query(""), domain: str = Query("")):
    from local_kb.db import search_entries
    conn = _get_db()
    entries = search_entries(conn, q, domain=domain or None, limit=20)
    return [
        {
            "id": e.id, "title": e.title, "domain": e.domain.value,
            "summary": e.summary[:200], "tags": e.tags,
            "confidence": e.confidence.value, "created": e.created.isoformat(),
        }
        for e in entries
    ]


@router.get("/api/stats")
async def api_stats():
    from local_kb.db import get_stats
    return get_stats(_get_db())
