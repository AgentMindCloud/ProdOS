"""Declarative base and shared mixins for all ORM models.

Every table uses a UUID primary key and ``created_at`` / ``updated_at``
timestamps, per the ProducerOS data model requirements. ``sqlalchemy.Uuid``
is used (rather than a dialect-specific type) so the same model definitions
work against SQLite (the default, local file) and PostgreSQL (documented as
supported "where practical").
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Uuid
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """A timezone-aware DateTime that round-trips correctly through SQLite.

    SQLite has no native datetime/timezone type, so a plain
    ``DateTime(timezone=True)`` column silently loses its ``tzinfo`` on
    read-back -- the value comes back naive, which then blows up any
    comparison against ``datetime.now(timezone.utc)`` (e.g. lockout/expiry
    checks) with "can't compare offset-naive and offset-aware datetimes".
    This type always stores naive UTC and always returns UTC-aware values,
    so every column is timezone-safe regardless of dialect.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class Base(DeclarativeBase):
    pass


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utcnow, onupdate=utcnow, nullable=False
    )
