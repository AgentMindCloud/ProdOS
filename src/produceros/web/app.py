"""FastAPI application factory."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from produceros.config import get_settings
from produceros.logging_config import configure_logging, get_logger
from produceros.security import SECURITY_HEADERS, generate_csrf_token
from produceros.web.csrf import CSRF_COOKIE_MAX_AGE, CSRF_COOKIE_NAME
from produceros.web.deps import AuthRedirect

WEB_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
logger = get_logger("web")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.logs_dir, settings.log_level)

    app = FastAPI(title="ProducerOS", docs_url=None, redoc_url=None, openapi_url=None)

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.exception_handler(AuthRedirect)
    async def _auth_redirect_handler(request: Request, exc: AuthRedirect):
        return RedirectResponse(url=exc.location, status_code=303)

    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response

    @app.middleware("http")
    async def csrf_cookie_middleware(request: Request, call_next):
        """Issues (or reuses) this browser's CSRF token *before* the route
        runs, so templates can render it into forms, then attaches the
        Set-Cookie header to whatever response object the route actually
        returns -- a plain ``response: Response`` dependency parameter
        does NOT get merged into a route's own returned Response, so this
        has to happen here rather than per-route."""
        existing = request.cookies.get(CSRF_COOKIE_NAME)
        token = existing or generate_csrf_token()
        request.state.csrf_token = token
        response = await call_next(request)
        if not existing:
            response.set_cookie(
                CSRF_COOKIE_NAME, token, httponly=True, samesite="lax",
                secure=request.url.scheme == "https", max_age=CSRF_COOKIE_MAX_AGE,
            )
        return response

    from produceros.web.routes import (
        analytics as analytics_routes,
        auth as auth_routes,
        backup as backup_routes,
        calendar as calendar_routes,
        catalog as catalog_routes,
        dashboard as dashboard_routes,
        delivery as delivery_routes,
        lan as lan_routes,
        marketing as marketing_routes,
        pwa as pwa_routes,
        releases as release_routes,
        scanner as scanner_routes,
        search as search_routes,
        settings as settings_routes,
    )

    app.include_router(pwa_routes.router)
    app.include_router(auth_routes.router)
    app.include_router(dashboard_routes.router)
    app.include_router(catalog_routes.router)
    app.include_router(scanner_routes.router)
    app.include_router(release_routes.router)
    app.include_router(marketing_routes.router)
    app.include_router(calendar_routes.router)
    app.include_router(delivery_routes.router)
    app.include_router(analytics_routes.router)
    app.include_router(backup_routes.router)
    app.include_router(settings_routes.router)
    app.include_router(lan_routes.router)
    app.include_router(search_routes.router)

    logger.info("ProducerOS application initialized (env=%s)", settings.app_env)
    return app
