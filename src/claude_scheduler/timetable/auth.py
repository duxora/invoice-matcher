"""Google OAuth 2.0 authentication for Family Timetable."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env early so auth config is available at import time
_config_env = Path.home() / ".config" / "claude-scheduler" / ".env"
if _config_env.exists():
    load_dotenv(_config_env)
else:
    load_dotenv()

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth

auth_router = APIRouter(prefix="/auth")

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
ALLOWED_EMAILS: set[str] = set(
    e.strip() for e in os.environ.get("ALLOWED_EMAILS", "").split(",") if e.strip()
)
AUTH_ENABLED = bool(GOOGLE_CLIENT_ID)

# Public paths that skip auth
PUBLIC_PATHS = {"/auth/login", "/auth/callback", "/auth/logout", "/static"}

oauth = OAuth()
if AUTH_ENABLED:
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def is_email_allowed(email: str) -> bool:
    """Check if email is in the allowlist. If no allowlist configured, allow all."""
    if not ALLOWED_EMAILS:
        return True  # no restriction if not configured
    return email in ALLOWED_EMAILS


async def require_auth(request: Request, call_next):
    """Middleware: redirect to login if not authenticated, catch Google Sheets errors."""
    if not AUTH_ENABLED:
        try:
            return await call_next(request)
        except PermissionError:
            # Google Sheets permission error — show setup page
            from fastapi.responses import HTMLResponse
            return HTMLResponse(
                content=_setup_error_html(str("Google Sheets permission denied. "
                    "Share the spreadsheet with your service account email as Editor.")),
                status_code=200,
            )

    path = request.url.path
    if any(path.startswith(p) for p in PUBLIC_PATHS):
        return await call_next(request)

    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/auth/login", status_code=307)

    request.state.user = user
    try:
        return await call_next(request)
    except PermissionError:
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content=_setup_error_html("Google Sheets permission denied. "
                "Share the spreadsheet with your service account email as Editor."),
            status_code=200,
        )


def _setup_error_html(error: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><title>Setup Required</title>
<script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-gray-900 text-gray-100 min-h-screen flex items-center justify-center p-4">
<div class="max-w-xl bg-gray-800 border border-yellow-500/30 rounded-lg p-8">
  <h1 class="text-2xl font-bold mb-4 text-yellow-400">Setup Required</h1>
  <p class="text-gray-400 mb-4">Could not connect to Google Sheets:</p>
  <div class="bg-gray-900 rounded p-4 mb-4 text-sm text-red-400 font-mono">{error}</div>
  <ol class="list-decimal list-inside space-y-2 text-gray-400 text-sm">
    <li>Create a Google Sheet with 4 tabs: <b>Tasks</b>, <b>Study</b>, <b>Reminders</b>, <b>Events</b></li>
    <li>Add header rows to each tab</li>
    <li><b>Share the sheet</b> with your service account email as Editor</li>
    <li>Set <code class="bg-gray-900 px-1 rounded">TIMETABLE_SPREADSHEET_ID</code> in <code>~/.config/claude-scheduler/.env</code></li>
  </ol>
  <a href="/timetable/" class="mt-6 inline-block px-4 py-2 bg-blue-600 rounded text-white text-sm hover:bg-blue-700">Retry</a>
</div></body></html>"""


@auth_router.get("/login")
async def login(request: Request):
    """Redirect to Google OAuth login."""
    redirect_uri = str(request.url_for("auth_callback"))
    return await oauth.google.authorize_redirect(request, redirect_uri)


@auth_router.get("/callback")
async def auth_callback(request: Request):
    """Handle Google OAuth callback."""
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo", {})
    email = userinfo.get("email", "")

    if not is_email_allowed(email):
        return RedirectResponse(url="/auth/login?error=not_allowed")

    request.session["user"] = {
        "email": email,
        "name": userinfo.get("name", email),
        "picture": userinfo.get("picture", ""),
    }
    return RedirectResponse(url="/")


@auth_router.get("/logout")
async def logout(request: Request):
    """Clear session and redirect to login."""
    request.session.clear()
    return RedirectResponse(url="/auth/login")
