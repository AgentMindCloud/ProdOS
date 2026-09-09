"""Local developer preview with byte-range audio and the deployment CSP.

Run: python scripts/preview_website.py
This server is a local development tool, never part of the public site bundle.
Hostinger serves the generated files directly.
"""

from pathlib import Path

import uvicorn
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles

BUILT = Path(__file__).resolve().parents[1] / ".work/website-dist"
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "media-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; "
    "form-action 'none'; frame-ancestors 'none'"
)


class PreviewHeaders(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = CSP
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.url.path.endswith(".zip"):
            response.headers["Content-Type"] = "application/zip"
            response.headers["Content-Disposition"] = "attachment"
        return response


def create_app():
    return Starlette(
        routes=[Mount("/", app=StaticFiles(directory=BUILT, html=True))],
        middleware=[Middleware(PreviewHeaders)],
    )


if __name__ == "__main__":
    uvicorn.run(create_app(), host="127.0.0.1", port=8427, log_level="warning")
