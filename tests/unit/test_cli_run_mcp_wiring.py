"""Regression test for a real wiring bug: `produceros.mcp_server.server
.run_mcp_server_blocking` existed and was fully built, but `cli.cmd_run`
never called it -- enabling MCP in config had no effect. This checks that
`produceros run` actually starts the MCP server thread when
`mcp_enabled` is set, without spinning up real servers."""

from __future__ import annotations

import threading
import time

from produceros.cli import main
from produceros.config import reset_settings_cache


def test_run_starts_mcp_server_thread_when_enabled(data_dir, monkeypatch):
    monkeypatch.setenv("PRODUCEROS_MCP_ENABLED", "true")
    reset_settings_cache()

    started = threading.Event()

    def fake_run_mcp_server_blocking() -> None:
        started.set()

    def fake_uvicorn_run(*args, **kwargs) -> None:
        return None

    monkeypatch.setattr(
        "produceros.mcp_server.server.run_mcp_server_blocking", fake_run_mcp_server_blocking
    )
    monkeypatch.setattr("uvicorn.run", fake_uvicorn_run)

    main(["run", "--no-browser"])

    assert started.wait(timeout=5), "run_mcp_server_blocking was never called by `produceros run`"


def test_run_does_not_start_mcp_server_thread_when_disabled(data_dir, monkeypatch):
    reset_settings_cache()  # mcp_enabled defaults to False

    calls: list[None] = []

    def fake_run_mcp_server_blocking() -> None:
        calls.append(None)

    def fake_uvicorn_run(*args, **kwargs) -> None:
        return None

    monkeypatch.setattr(
        "produceros.mcp_server.server.run_mcp_server_blocking", fake_run_mcp_server_blocking
    )
    monkeypatch.setattr("uvicorn.run", fake_uvicorn_run)

    main(["run", "--no-browser"])
    time.sleep(0.2)

    assert calls == []
