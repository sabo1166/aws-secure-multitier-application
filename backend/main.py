"""Application factory. Run locally:  uvicorn backend.main:create_app --factory --reload"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from .config import Settings, load_dotenv, resolve_session_secret
from .database import build_database_url, make_engine, make_session_factory
from .deps import money, render
from .models import Base
from .paths import FRONTEND_DIR
from .routes import cart, misc, pages, products
from .security import CSP
from .seed import seed_if_empty
from .services.cart import CartError

log = logging.getLogger("sole_atelier")

STATUS_TEXT = {
    400: "That request could not be understood.",
    403: "You do not have permission to do that.",
    404: "We could not find the page you were looking for.",
    405: "That action is not supported here.",
    409: "That could not be completed.",
    422: "Some of the information sent was not valid.",
    503: "The store is temporarily unavailable. Please try again shortly.",
}


def friendly(error: dict) -> str:
    """Short human wording for validation errors. Never includes the submitted value."""
    kind, ctx = error.get("type", ""), error.get("ctx", {})
    if kind == "missing":
        return "This field is required."
    if kind == "string_too_short":
        return f"Please enter at least {ctx.get('min_length')} characters."
    if kind == "string_too_long":
        return f"Please use at most {ctx.get('max_length')} characters."
    if kind == "string_pattern_mismatch":
        return "Please check this value; it contains characters or a format we cannot accept."
    if "email" in error.get("msg", "").lower():
        return "Enter a valid email address."
    if kind == "extra_forbidden":
        return "This field is not accepted."
    return "This value is not valid."


def create_app(settings: Settings | None = None, engine: Engine | None = None) -> FastAPI:
    if settings is None:
        load_dotenv()
        settings = Settings.from_env()
    settings.validate()
    settings = resolve_session_secret(settings)

    if engine is None:
        engine = make_engine(build_database_url(settings), settings)
    session_secret = settings.session_secret or "development-only-not-for-production-use"

    app = FastAPI(title="SOLE ATELIER", docs_url=None if settings.is_production else "/docs", redoc_url=None, openapi_url=None if settings.is_production else "/openapi.json")
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    templates = Jinja2Templates(directory=str(FRONTEND_DIR / "templates"))
    templates.env.filters["money"] = money
    app.state.templates = templates

    # Development convenience only. In production the schema is created explicitly (python -m backend.init_db).
    if not settings.is_production and str(engine.url).startswith("sqlite"):
        Base.metadata.create_all(engine)
        with app.state.session_factory() as db:
            seed_if_empty(db)

    app.add_middleware(
        SessionMiddleware, secret_key=session_secret, session_cookie="sole_session",
        same_site="lax", https_only=settings.session_https_only, max_age=60 * 60 * 24 * 14,
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = CSP
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.url.path.startswith(("/api", "/cart", "/checkout", "/orders")):
            response.headers["Cache-Control"] = "no-store"
        return response

    def wants_json(request: Request) -> bool:
        return request.url.path.startswith("/api") or request.url.path.startswith("/health")

    def error_response(request: Request, status: int, code: str, message: str, details=None):
        if wants_json(request):
            body = {"error": {"code": code, "message": message}}
            if details:
                body["error"]["details"] = details
            return JSONResponse(body, status_code=status)
        return render(request, "error.html", status_code=status, status=status, message=message)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        message = exc.detail if wants_json(request) and isinstance(exc.detail, str) else STATUS_TEXT.get(exc.status_code, "Something went wrong.")
        return error_response(request, exc.status_code, f"http_{exc.status_code}", message)

    @app.exception_handler(CartError)
    async def cart_error(request: Request, exc: CartError):
        return error_response(request, exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Only field names and messages are returned: never the submitted values or internals.
        details = [{"field": ".".join(str(p) for p in e["loc"][1:]) or str(e["loc"][0]), "message": friendly(e)} for e in exc.errors()]
        return error_response(request, 422, "validation_error", "Some of the information sent was not valid.", details)

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError):
        log.error("database error on %s %s: %s", request.method, request.url.path, type(exc).__name__)
        return error_response(request, 503, "database_unavailable", STATUS_TEXT[503])

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        log.exception("unhandled error on %s %s", request.method, request.url.path)
        return error_response(request, 500, "internal_error", "Something went wrong on our side.")

    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR / "static")), name="static")
    app.include_router(pages.router)
    app.include_router(products.router)
    app.include_router(cart.router)
    app.include_router(misc.api)
    app.include_router(misc.health)
    return app


# No module-level `app`: importing this module must not touch a database.
# Run with:  uvicorn backend.main:create_app --factory
