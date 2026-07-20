"""CSRF protection via the double-submit cookie pattern (spec section 19).

A random token is stored in an httponly cookie (issued by the middleware
in web.app, one per browser, reused across requests) and the same value
is rendered into every form as a hidden field. On POST, the two must
match. Since the cookie is httponly, an attacker's cross-site form can't
read it to forge a matching hidden field.
"""

from __future__ import annotations

from fastapi import Request

from produceros.security import constant_time_equals

CSRF_COOKIE_NAME = "produceros_csrf"
CSRF_COOKIE_MAX_AGE = 60 * 60 * 24 * 7


def get_csrf_token(request: Request) -> str:
    """Return this request's CSRF token (set by the middleware in
    web.app onto ``request.state.csrf_token`` before the route runs)."""
    return request.state.csrf_token


def verify_csrf(request: Request, submitted_token: object) -> bool:
    """Accepts whatever ``form.get("csrf_token")`` returned -- Starlette
    types that as ``UploadFile | str | None``, and anything that isn't a
    plain string (including a maliciously-uploaded file field named
    ``csrf_token``) is simply an invalid token."""
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    if not cookie_token or not isinstance(submitted_token, str) or not submitted_token:
        return False
    return constant_time_equals(cookie_token, submitted_token)
