"""Global search and locally stored saved filters (spec section 23).

Saved filters reuse the generic AppSetting key/value store (namespaced
under ``saved_filter:``) rather than a dedicated table -- there's nothing
relational about a saved filter beyond "a name and a query string."
"""

from __future__ import annotations

import json
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from produceros.models.catalog import Artist, Project
from produceros.models.release import Release
from produceros.services.settings import delete_setting, list_settings_by_prefix, set_setting

SAVED_FILTER_PREFIX = "saved_filter:"


def global_search(session: Session, query: str) -> dict[str, list]:
    like = f"%{query.strip()}%"
    projects = list(
        session.scalars(
            select(Project).where(
                Project.working_title.ilike(like) | Project.final_title.ilike(like) | Project.internal_code.ilike(like)
            ).limit(20)
        )
    )
    artists = list(session.scalars(select(Artist).where(Artist.name.ilike(like)).limit(20)))
    releases = list(session.scalars(select(Release).where(Release.title.ilike(like)).limit(20)))
    return {"projects": projects, "artists": artists, "releases": releases}


def save_filter(session: Session, name: str, query_string: str) -> None:
    set_setting(session, f"{SAVED_FILTER_PREFIX}{uuid.uuid4()}", {"name": name, "query": query_string})


def list_saved_filters(session: Session) -> list[dict]:
    rows = list_settings_by_prefix(session, SAVED_FILTER_PREFIX)
    result = []
    for row in rows:
        try:
            payload = json.loads(row.value)
        except (json.JSONDecodeError, TypeError):
            continue
        result.append({"key": row.key, "name": payload.get("name"), "query": payload.get("query")})
    return result


def delete_saved_filter(session: Session, key: str) -> None:
    delete_setting(session, key)
