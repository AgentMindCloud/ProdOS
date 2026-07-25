"""Regression test for a real wiring bug: `produceros.mcp_server.server
.run_mcp_server_blocking` existed and was fully built, but `cli.cmd_run`
never called it -- enabling MCP in config had no effect. This checks that
`produceros run` actually starts the MCP server thread when
`mcp_enabled` is set, without spinning up real servers.

Two things these tests must never do, both learned the hard way:

* **Never leave uvicorn unstubbed.** ``cmd_run`` builds a
  ``uvicorn.Server`` explicitly (so the in-app quit button has something
  to stop), so stubbing ``uvicorn.run`` is not enough -- it stubs a
  function ``cmd_run`` no longer calls, and the test then starts a *real*
  server that blocks until pytest is killed.
* **Never use the default port.** ``cmd_run`` now probes the port before
  binding, so a test on the default port passes or fails depending on
  whether anything happens to be running on this machine. Each test picks
  a free port instead.
"""

from __future__ import annotations

import socket
import threading
import time

import pytest

from produceros.cli import main
from produceros.config import reset_settings_cache


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def stub_uvicorn(monkeypatch):
    """Stop ``cmd_run`` short of actually serving, and record that it got there."""
    served = threading.Event()

    def fake_server_run(self) -> None:
        served.set()

    monkeypatch.setattr("uvicorn.Server.run", fake_server_run)
    return served


def test_run_starts_mcp_server_thread_when_enabled(data_dir, monkeypatch, stub_uvicorn):
    monkeypatch.setenv("PRODUCEROS_MCP_ENABLED", "true")
    reset_settings_cache()

    started = threading.Event()
    monkeypatch.setattr(
        "produceros.mcp_server.server.run_mcp_server_blocking", lambda: started.set()
    )

    main(["run", "--no-browser", "--port", str(_free_port())])

    assert stub_uvicorn.is_set(), "cmd_run returned before it tried to serve"
    assert started.wait(timeout=5), "run_mcp_server_blocking was never called by `produceros run`"


def test_run_does_not_start_mcp_server_thread_when_disabled(data_dir, monkeypatch, stub_uvicorn):
    reset_settings_cache()  # mcp_enabled defaults to False

    calls: list[None] = []
    monkeypatch.setattr(
        "produceros.mcp_server.server.run_mcp_server_blocking", lambda: calls.append(None)
    )

    main(["run", "--no-browser", "--port", str(_free_port())])
    time.sleep(0.2)

    assert stub_uvicorn.is_set(), "cmd_run returned before it tried to serve"
    assert calls == []
