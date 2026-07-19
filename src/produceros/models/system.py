from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from produceros.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin
from produceros.models.enums import BackupType


class AuditEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Append-only audit log. Every state change, security event, and
    file/data operation ProducerOS performs is recorded here."""

    __tablename__ = "audit_events"

    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    device_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("paired_devices.id"))
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(100))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(64))


class AppSetting(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-encoded


class BackupRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "backup_records"

    backup_type: Mapped[BackupType] = mapped_column(
        SAEnum(BackupType, native_enum=False, validate_strings=True),
        default=BackupType.MANUAL,
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    notes: Mapped[str | None] = mapped_column(Text)
