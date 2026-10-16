"""CSRF protection (synchroniser token kept in the signed session) and security headers."""
from __future__ import annotations

import hmac
import secrets

from fastapi import HTTPException, Request

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

CSP = (
    "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; font-src 'self'; "
    "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)


def csrf_token(request: Request) -> str:
    token = request.session.get("csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf"] = token
    return token


async def require_csrf(request: Request) -> None:
    """Router dependency: state-changing requests must echo the session token in X-CSRF-Token."""
    if request.method in SAFE_METHODS:
        return
    expected = request.session.get("csrf", "")
    supplied = request.headers.get("x-csrf-token", "")
    if not expected or not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=403, detail="Missing or invalid CSRF token")
