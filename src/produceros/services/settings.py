"""Key/value application settings stored in the database (AppSetting).

Distinct from produceros.config.Settings (process configuration loaded
from env/config.toml at startup): this module holds small pieces of state
the running application changes at runtime, e.g. "has first-run setup
completed", "which project states are visible", scanner root list edited
from the Settings page, etc.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from produceros.models.system import AppSetting

FIRST_RUN_COMPLETE_KEY = "first_run_complete"
VISIBLE_PROJECT_STATES_KEY = "visible_project_states"


def get_setting(session: Session, key: str, default: Any = None) -> Any:
    row = session.scalar(select(AppSetting).where(AppSetting.key == key))
    if row is None:
        return default
    try:
        return json.loads(row.value)
    except (json.JSONDecodeError, TypeError):
        return default


def set_setting(session: Session, key: str, value: Any) -> AppSetting:
    row = session.scalar(select(AppSetting).where(AppSetting.key == key))
    encoded = json.dumps(value)
    if row is None:
        row = AppSetting(key=key, value=encoded)
        session.add(row)
    else:
        row.value = encoded
    session.flush()
    return row


def is_first_run_complete(session: Session) -> bool:
    return bool(get_setting(session, FIRST_RUN_COMPLETE_KEY, default=False))


def mark_first_run_complete(session: Session) -> None:
    set_setting(session, FIRST_RUN_COMPLETE_KEY, True)


def list_settings_by_prefix(session: Session, prefix: str) -> list[AppSetting]:
    return list(session.scalars(select(AppSetting).where(AppSetting.key.startswith(prefix))))


def delete_setting(session: Session, key: str) -> None:
    row = session.scalar(select(AppSetting).where(AppSetting.key == key))
    if row is not None:
        session.delete(row)
        session.flush()
