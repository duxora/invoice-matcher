"""Tests for Google OAuth middleware."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware


def make_test_app(auth_enabled: bool = True):
    """Create a test app with auth middleware.

    Patches AUTH_ENABLED at the module level so the middleware
    behaves correctly regardless of env vars at import time.
    """
    from claude_scheduler.timetable.auth import require_auth, auth_router

    app = FastAPI()
    app.include_router(auth_router)

    @app.get("/protected")
    async def protected(request: Request):
        user = getattr(request.state, "user", {"email": "anonymous"})
        return {"user": user}

    # Patch AUTH_ENABLED before adding the middleware decorator.
    # Use app.middleware("http") which adds BaseHTTPMiddleware internally.
    # Middleware added via add_middleware is outermost-last, but
    # app.middleware("http") also prepends. We need SessionMiddleware
    # to wrap auth, so we register auth first, then session.
    @app.middleware("http")
    async def _auth_middleware(request: Request, call_next):
        with patch("claude_scheduler.timetable.auth.AUTH_ENABLED", auth_enabled):
            return await require_auth(request, call_next)

    # SessionMiddleware added last = outermost, so session scope is
    # available when auth middleware runs.
    app.add_middleware(SessionMiddleware, secret_key="test-secret")
    return app


def test_unauthenticated_redirects_to_login():
    """When AUTH_ENABLED and no session, redirect to /auth/login."""
    app = make_test_app(auth_enabled=True)
    client = TestClient(app, follow_redirects=False)
    resp = client.get("/protected")
    assert resp.status_code == 307
    assert "/auth/login" in resp.headers["location"]


def test_auth_disabled_passes_through():
    """When AUTH_ENABLED is False, requests pass through without auth."""
    app = make_test_app(auth_enabled=False)
    client = TestClient(app)
    resp = client.get("/protected")
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == "anonymous"


def test_public_paths_skip_auth():
    """Public paths like /auth/logout should not require auth."""
    app = make_test_app(auth_enabled=True)
    client = TestClient(app, follow_redirects=False)
    resp = client.get("/auth/logout")
    # Logout redirects to /auth/login, but should not get a 307 from middleware
    assert resp.status_code == 307
    assert "/auth/login" in resp.headers["location"]


def test_allowed_emails_check():
    """is_email_allowed respects the ALLOWED_EMAILS set."""
    from claude_scheduler.timetable.auth import is_email_allowed

    with patch(
        "claude_scheduler.timetable.auth.ALLOWED_EMAILS",
        {"duc@example.com", "wife@example.com"},
    ):
        assert is_email_allowed("duc@example.com") is True
        assert is_email_allowed("wife@example.com") is True
        assert is_email_allowed("stranger@example.com") is False


def test_allowed_emails_empty_allows_all():
    """When ALLOWED_EMAILS is empty, all emails are allowed."""
    from claude_scheduler.timetable.auth import is_email_allowed

    with patch("claude_scheduler.timetable.auth.ALLOWED_EMAILS", set()):
        assert is_email_allowed("anyone@example.com") is True
