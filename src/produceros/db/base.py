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
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
