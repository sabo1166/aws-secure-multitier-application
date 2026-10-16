"""Shared request helpers: DB session, settings, and template rendering with common context."""
from __future__ import annotations

from decimal import Decimal
from typing import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from .config import Settings
from .security import csrf_token
from .services import cart as cart_service
from .services.catalog import COLLECTIONS


def get_db(request: Request) -> Iterator[Session]:
    db = request.app.state.session_factory()
    try:
        yield db
    finally:
        db.close()


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def money(value) -> str:
    return f"${Decimal(value):,.2f}"


def render(request: Request, template: str, status_code: int = 200, **context):
    settings: Settings = request.app.state.settings
    base = {
        "store_name": settings.store_name,
        "csrf_token": csrf_token(request),
        "cart_count": cart_service.raw_count(request.session),
        "collections": COLLECTIONS,
    }
    response = request.app.state.templates.TemplateResponse(request, template, {**base, **context}, status_code=status_code)
    return response
