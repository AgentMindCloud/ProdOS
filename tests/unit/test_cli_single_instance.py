"""`produceros run` when the port is already taken.

The behaviour that matters for a non-technical user: double-clicking the
desktop icon while ProducerOS is *already* running used to reach
`uvicorn.run`, fail to bind, and raise `SystemExit(1)`. In a windowed
Windows build that means no console, no message box (launcher.py
re-raises SystemExit without showing one), and no browser -- clicking the
icon appeared to do nothing at all. Now it re-opens the browser instead.
"""

from __future__ import annotations

import socket

import pytest

from produceros.cli import main
from produceros.config import reset_settings_cache


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def never_serves(monkeypatch):
    """Fail loudly if cmd_run tries to bind -- these tests are about the
    paths that must return *before* that."""

    def explode(self) -> None:
        raise AssertionError("cmd_run should not have tried to serve here")

    monkeypatch.setattr("uvicorn.Server.run", explode)


def test_second_launch_reopens_the_browser_instead_of_failing(
    data_dir, monkeypatch, never_serves, tmp_path
):
    reset_settings_cache()
    port = _free_port()

    # Stand in for an already-running ProducerOS answering the health probe.
    monkeypatch.setattr("produceros.cli._probe_running_instance", lambda host, p, **kw: True)

    opened: list[str] = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url))

    main(["run", "--port", str(port)])  # note: browser opening left enabled

    assert opened == [
        f"http://127.0.0.1:{port}/"
    ], "a second launch should re-open the running app in the browser"


def test_second_launch_respects_no_browser(data_dir, monkeypatch, never_serves):
    reset_settings_cache()
    monkeypatch.setattr("produceros.cli._probe_running_instance", lambda host, p, **kw: True)

    opened: list[str] = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url))

    main(["run", "--no-browser", "--port", str(_free_port())])

    assert opened == []


def test_port_held_by_another_program_reports_a_clear_error(data_dir, monkeypatch, never_serves):
    """A non-ProducerOS squatter must produce an actionable message, not a
    bare SystemExit -- launcher.py turns exceptions into a message box but
    deliberately lets SystemExit pass through silently."""
    reset_settings_cache()

    squatter = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    squatter.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    squatter.bind(("127.0.0.1", 0))
    squatter.listen(1)
    port = squatter.getsockname()[1]

    # Nothing ever accepts on this socket, so the health probe correctly
    # concludes "port is busy, but that isn't ProducerOS".
    try:
        with pytest.raises(RuntimeError) as excinfo:
            main(["run", "--no-browser", "--port", str(port)])
    finally:
        squatter.close()

    message = str(excinfo.value)
    assert str(port) in message
    assert "already being used" in message
    assert "--port" in message, "the error should tell the user how to pick another port"
