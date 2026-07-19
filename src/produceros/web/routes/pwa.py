"""PWA plumbing: the service worker (served at root scope) and the
offline app-shell fallback page (spec section 17)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from produceros.web.app import STATIC_DIR, templates

router = APIRouter(tags=["pwa"])


@router.get("/service-worker.js")
async def service_worker() -> FileResponse:
    response = FileResponse(STATIC_DIR / "service-worker.js", media_type="application/javascript")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response


@router.get("/offline.html")
async def offline_shell(request: Request):
    return templates.TemplateResponse(request, "offline.html", {})
