"""Engine and session factory.

SQLite is opened with WAL mode by default (per spec) for better read
concurrency between the web app and background scanner threads. The engine
is created lazily and cached so tests can override the database URL before
first use.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from produceros.config import get_settings


def _build_engine(database_url: str, wal_mode: bool) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args, future=True)

    if database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection, _connection_record):  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            if wal_mode:
                cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    return engine


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    settings.ensure_directories()
    return _build_engine(settings.database_url, settings.db_wal_mode)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def reset_engine_cache() -> None:
    """Dispose of and clear cached engine/sessionmaker (used by tests)."""
    try:
        get_engine().dispose()
    except Exception:
        pass
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a request-scoped session."""
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Context manager for scripts/services that commits or rolls back."""
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
