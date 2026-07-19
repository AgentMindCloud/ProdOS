"""Shared template context merged into every authenticated page render."""

from __future__ import annotations

from produceros.config import get_settings
from produceros.models.user import User


def base_context(user: User | None, active_nav: str = "") -> dict:
    settings = get_settings()
    return {
        "current_user": user,
        "active_nav": active_nav,
        "lan_mode": settings.bind_mode == "lan",
    }
