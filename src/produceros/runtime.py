"""Process-level runtime controls shared between the CLI and the web app.

ProducerOS ships as a windowed Windows build (no console), so there is no
Ctrl+C and no window to close -- without an explicit in-app quit, the only
way to stop the server would be Task Manager. That also matters for
updates: the installer has to replace files the running process holds
open, so the user needs a real way to shut it down first.

``cmd_run`` registers a hook that flips uvicorn's ``should_exit`` flag;
the Settings page calls ``request_shutdown()``. Kept in its own module so
the web layer never has to import the CLI (which would be a circular
import) just to stop the server.
"""

from __future__ import annotations

from collections.abc import Callable

_shutdown_hook: Callable[[], None] | None = None


def set_shutdown_hook(hook: Callable[[], None] | None) -> None:
    global _shutdown_hook
    _shutdown_hook = hook


def can_shut_down() -> bool:
    """False when nothing owns the server loop -- e.g. under TestClient, or
    when the app is hosted by something other than ``produceros run``."""
    return _shutdown_hook is not None


def request_shutdown() -> bool:
    """Ask the running server to stop. Returns False if that isn't possible
    here, so the caller can say so instead of pretending it worked."""
    if _shutdown_hook is None:
        return False
    _shutdown_hook()
    return True
