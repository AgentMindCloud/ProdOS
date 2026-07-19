"""Shared pytest fixtures.

Every test gets an isolated data directory (a fresh temp dir per test,
never the developer's real ProducerOS data) and a fresh, cache-reset
Settings/engine, so tests never see each other's state.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from sqlalchemy.orm import Session

from produceros.config import reset_settings_cache
from produceros.db.base import Base
from produceros.db.session import get_engine, get_sessionmaker, reset_engine_cache


@pytest.fixture
def data_dir(tmp_path, monkeypatch) -> Generator:
    monkeypatch.setenv("PRODUCEROS_DATA_DIR", str(tmp_path / "produceros-data"))
    reset_settings_cache()
    reset_engine_cache()
    yield tmp_path / "produceros-data"
    reset_engine_cache()
    reset_settings_cache()


@pytest.fixture
def db_session(data_dir) -> Generator[Session, None, None]:
    engine = get_engine()
    Base.metadata.create_all(engine)
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def admin_user(db_session):
    from produceros.services.auth import create_first_admin

    user = create_first_admin(db_session, username="producer", password="correcthorsebattery", display_name="Test Producer")
    db_session.commit()
    return user


@pytest.fixture
def client(data_dir):
    """A FastAPI TestClient wired to the isolated per-test database."""
    from fastapi.testclient import TestClient

    from produceros.web.app import create_app

    engine = get_engine()
    Base.metadata.create_all(engine)

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def complete_setup(client, username="producer", password="correcthorsebattery") -> None:
    """Helper: run first-run setup through the real HTTP flow and leave
    the client's cookie jar authenticated."""
    import re

    r = client.get("/setup")
    csrf_token = re.search(r'name="csrf_token" value="([^"]+)"', r.text).group(1)
    client.post(
        "/setup",
        data={
            "csrf_token": csrf_token,
            "display_name": "Test Producer",
            "username": username,
            "password": password,
            "password_confirm": password,
        },
    )


def get_form_csrf(client, path: str) -> str:
    import re

    r = client.get(path)
    match = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    assert match, f"No CSRF token found on {path}"
    return match.group(1)


@pytest.fixture
def random_uuid() -> uuid.UUID:
    return uuid.uuid4()
