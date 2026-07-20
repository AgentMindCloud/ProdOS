"""Fixtures for driving a real, live ProducerOS server with Playwright.

Each test gets its own isolated data directory and its own uvicorn server
bound to 127.0.0.1 on a free port, run in a background thread -- this is a
full HTTP + browser round trip, not a TestClient shortcut, so it's the only
suite that actually exercises the PWA shell, static assets, and JS in a
real browser.
"""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Generator

import pytest
import uvicorn
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="session")
def browser():
    # This environment pre-installs Chromium at a fixed path/version rather
    # than whatever version this project's pinned `playwright` package would
    # try to download, so launch it explicitly instead of downloading.
    with sync_playwright() as p:
        chromium = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        yield chromium
        chromium.close()


@pytest.fixture
def make_page(browser):
    """Create pages with a generous default timeout. Playwright's 30s
    default has proven flaky for form-submit navigations when the whole
    suite runs back-to-back on a loaded machine; 60s keeps a genuine hang
    detectable while absorbing slow-CI jitter."""
    pages = []

    def _make(**kwargs):
        page = browser.new_page(**kwargs)
        page.set_default_timeout(60_000)
        page.set_default_navigation_timeout(60_000)
        pages.append(page)
        return page

    yield _make
    for page in pages:
        page.close()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def live_server(tmp_path, monkeypatch) -> Generator[str, None, None]:
    import produceros.models  # noqa: F401 -- registers every table on Base.metadata
    from produceros.config import reset_settings_cache
    from produceros.db.base import Base
    from produceros.db.session import get_engine, get_sessionmaker, reset_engine_cache

    monkeypatch.setenv("PRODUCEROS_DATA_DIR", str(tmp_path / "produceros-data"))
    reset_settings_cache()
    reset_engine_cache()

    engine = get_engine()
    Base.metadata.create_all(engine)
    get_sessionmaker()

    from produceros.web.app import create_app

    app = create_app()
    port = _free_port()
    # Access logs stay on: pytest only shows captured output on failure,
    # and knowing whether a request reached the server is the first
    # question when an e2e navigation times out.
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="info", access_log=True)
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                break
        except OSError:
            time.sleep(0.1)
    else:
        raise RuntimeError("Live ProducerOS server did not start in time.")

    try:
        yield base_url
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        reset_engine_cache()
        reset_settings_cache()
