from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from produceros.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin
from produceros.models.enums import DeviceStatus


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """The single local administrator account.

    ProducerOS uses a single-user local security model (spec section 19);
    the schema allows for more than one row, but the app only ever
    provisions one during first-run setup.
    """

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(UTCDateTime)

    devices: Mapped[list["PairedDevice"]] = relationship(back_populates="user")


class PairedDevice(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An Android/other device paired for LAN-mode access.

    A pairing code is issued (hashed at rest) with a short expiry; once the
    device submits the correct code it is promoted to ``active`` and given
    a long-lived, revocable session token (also hashed at rest).
    """

    __tablename__ = "paired_devices"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    device_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[DeviceStatus] = mapped_column(
        SAEnum(DeviceStatus, native_enum=False, validate_strings=True),
        default=DeviceStatus.PENDING,
        nullable=False,
    )
    pairing_code_hash: Mapped[str | None] = mapped_column(String(256))
    pairing_code_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    session_token_hash: Mapped[str | None] = mapped_column(String(256))
    session_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_seen_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_seen_ip: Mapped[str | None] = mapped_column(String(64))
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    user: Mapped[User] = relationship(back_populates="devices")
