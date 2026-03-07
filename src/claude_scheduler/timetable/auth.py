"""Google OAuth 2.0 authentication for Family Timetable."""
import os

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
    """Middleware: redirect to login if not authenticated."""
    if not AUTH_ENABLED:
        return await call_next(request)

    path = request.url.path
    if any(path.startswith(p) for p in PUBLIC_PATHS):
        return await call_next(request)

    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/auth/login", status_code=307)

    request.state.user = user
    return await call_next(request)


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
    return RedirectResponse(url="/timetable/")


@auth_router.get("/logout")
async def logout(request: Request):
    """Clear session and redirect to login."""
    request.session.clear()
    return RedirectResponse(url="/auth/login")
