"""Android device pairing for LAN mode (spec sections 18-19).

New devices get a short-lived, rate-limited pairing code (never a
long-lived credential) shown as a QR code + human-typeable code on the
Windows screen. Confirming the code promotes the device to an active,
revocable session. Pairing-attempt rate limiting is kept in-process
(module-level, reset on restart) -- acceptable for a single-user local
LAN feature, and documented as such in docs/SECURITY_MODEL.md.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from produceros.models.enums import DeviceStatus
from produceros.models.user import PairedDevice, User
from produceros.security import (
    generate_pairing_code,
    generate_session_token,
    hash_password,
    verify_password,
)
from produceros.services.audit import log_event

_pairing_attempts: dict[str, list[datetime]] = defaultdict(list)
SESSION_LIFETIME_DAYS = 30
DEVICE_COOKIE_NAME = "produceros_device"
DEVICE_SALT = "produceros-device-v1"


class RateLimitedError(Exception):
    pass


class PairingError(ValueError):
    pass


def _check_rate_limit(ip_address: str, max_per_minute: int) -> None:
    now = datetime.now(UTC)
    window_start = now - timedelta(minutes=1)
    attempts = [t for t in _pairing_attempts[ip_address] if t > window_start]
    if len(attempts) >= max_per_minute:
        raise RateLimitedError("Too many pairing attempts. Please wait a minute.")
    attempts.append(now)
    _pairing_attempts[ip_address] = attempts


def start_pairing(
    session: Session, *, device_name: str, user_id: uuid.UUID, ttl_minutes: int
) -> tuple[PairedDevice, str]:
    code = generate_pairing_code()
    device = PairedDevice(
        user_id=user_id,
        device_name=device_name.strip() or "New device",
        status=DeviceStatus.PENDING,
        pairing_code_hash=hash_password(code),
        pairing_code_expires_at=datetime.now(UTC) + timedelta(minutes=ttl_minutes),
    )
    session.add(device)
    session.flush()
    log_event(
        session,
        event_type="lan.pairing_started",
        summary=f"Pairing started for device '{device.device_name}'.",
        user_id=user_id,
        entity_type="PairedDevice",
        entity_id=device.id,
    )
    return device, code


def confirm_pairing(
    session: Session,
    *,
    device_id: uuid.UUID,
    submitted_code: str,
    ip_address: str,
    max_attempts_per_minute: int,
) -> tuple[PairedDevice, str]:
    _check_rate_limit(ip_address, max_attempts_per_minute)

    device = session.get(PairedDevice, device_id)
    if device is None or device.status != DeviceStatus.PENDING:
        raise PairingError("Pairing request not found or already completed.")

    now = datetime.now(UTC)
    if device.pairing_code_expires_at is None or device.pairing_code_expires_at < now:
        device.status = DeviceStatus.EXPIRED
        session.flush()
        raise PairingError("This pairing code has expired. Start pairing again.")

    if not device.pairing_code_hash or not verify_password(
        device.pairing_code_hash, submitted_code
    ):
        log_event(
            session,
            event_type="lan.pairing_failed",
            summary=f"Incorrect pairing code submitted for device '{device.device_name}'.",
            entity_type="PairedDevice",
            entity_id=device.id,
            ip_address=ip_address,
        )
        raise PairingError("Incorrect pairing code.")

    token = generate_session_token()
    device.status = DeviceStatus.ACTIVE
    device.session_token_hash = hash_password(token)
    device.session_expires_at = now + timedelta(days=SESSION_LIFETIME_DAYS)
    device.pairing_code_hash = None
    device.pairing_code_expires_at = None
    device.last_seen_at = now
    device.last_seen_ip = ip_address
    session.flush()
    log_event(
        session,
        event_type="lan.pairing_confirmed",
        summary=f"Device '{device.device_name}' paired successfully.",
        entity_type="PairedDevice",
        entity_id=device.id,
        ip_address=ip_address,
    )
    return device, token


def verify_device_session(
    session: Session, device_id: uuid.UUID, token: str
) -> PairedDevice | None:
    device = session.get(PairedDevice, device_id)
    if device is None or device.status != DeviceStatus.ACTIVE:
        return None
    now = datetime.now(UTC)
    if device.session_expires_at is None or device.session_expires_at < now:
        return None
    if not device.session_token_hash or not verify_password(device.session_token_hash, token):
        return None
    device.last_seen_at = now
    session.flush()
    return device


def issue_device_cookie_token(secret_key: str, device: PairedDevice) -> str:
    """A signed cookie identifying *which device row* to check on each
    request. Actual authorization is always re-checked against the live
    ``PairedDevice.status`` in the database, so revocation takes effect
    immediately on the device's very next request -- there is no token
    denylist to maintain."""
    serializer = URLSafeTimedSerializer(secret_key, salt=DEVICE_SALT)
    return serializer.dumps({"device_id": str(device.id)})


def resolve_device_from_cookie(
    session: Session, secret_key: str, token: str, max_age_seconds: int
) -> User | None:
    serializer = URLSafeTimedSerializer(secret_key, salt=DEVICE_SALT)
    try:
        payload = serializer.loads(token, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None

    try:
        device_id = uuid.UUID(payload["device_id"])
    except (KeyError, ValueError, TypeError):
        return None

    device = session.get(PairedDevice, device_id)
    if device is None or device.status != DeviceStatus.ACTIVE:
        return None
    now = datetime.now(UTC)
    if device.session_expires_at is None or device.session_expires_at < now:
        return None

    device.last_seen_at = now
    session.flush()
    return device.user


def revoke_device(
    session: Session, device: PairedDevice, *, user_id: uuid.UUID | None = None
) -> PairedDevice:
    device.status = DeviceStatus.REVOKED
    device.revoked_at = datetime.now(UTC)
    device.session_token_hash = None
    session.flush()
    log_event(
        session,
        event_type="lan.device_revoked",
        summary=f"Device '{device.device_name}' access revoked.",
        user_id=user_id,
        entity_type="PairedDevice",
        entity_id=device.id,
    )
    return device


def list_devices(session: Session) -> list[PairedDevice]:
    from sqlalchemy import select

    return list(session.scalars(select(PairedDevice).order_by(PairedDevice.created_at.desc())))
