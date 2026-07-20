import uuid
from datetime import UTC, datetime, timedelta

import pytest

from produceros.models.enums import DeviceStatus
from produceros.services import pairing as pairing_service
from produceros.services.auth import create_first_admin


@pytest.fixture
def admin(db_session):
    return create_first_admin(
        db_session, username="producer", password="correcthorsebattery", display_name="Producer"
    )


def test_start_pairing_creates_pending_device_with_hashed_code(db_session, admin):
    device, code = pairing_service.start_pairing(
        db_session, device_name="My Phone", user_id=admin.id, ttl_minutes=10
    )
    assert device.status == DeviceStatus.PENDING
    assert device.pairing_code_hash is not None
    assert code not in device.pairing_code_hash


def test_confirm_pairing_with_correct_code_activates_device(db_session, admin):
    device, code = pairing_service.start_pairing(
        db_session, device_name="My Phone", user_id=admin.id, ttl_minutes=10
    )
    confirmed_device, token = pairing_service.confirm_pairing(
        db_session,
        device_id=device.id,
        submitted_code=code,
        ip_address="192.168.1.5",
        max_attempts_per_minute=5,
    )
    assert confirmed_device.status == DeviceStatus.ACTIVE
    assert confirmed_device.pairing_code_hash is None
    assert token


def test_confirm_pairing_with_wrong_code_fails(db_session, admin):
    device, _code = pairing_service.start_pairing(
        db_session, device_name="My Phone", user_id=admin.id, ttl_minutes=10
    )
    with pytest.raises(pairing_service.PairingError):
        pairing_service.confirm_pairing(
            db_session,
            device_id=device.id,
            submitted_code="WRONGCODE",
            ip_address="192.168.1.5",
            max_attempts_per_minute=5,
        )


def test_confirm_pairing_with_expired_code_fails(db_session, admin):
    device, code = pairing_service.start_pairing(
        db_session, device_name="My Phone", user_id=admin.id, ttl_minutes=10
    )
    device.pairing_code_expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.flush()
    with pytest.raises(pairing_service.PairingError):
        pairing_service.confirm_pairing(
            db_session,
            device_id=device.id,
            submitted_code=code,
            ip_address="192.168.1.5",
            max_attempts_per_minute=5,
        )


def test_pairing_attempts_are_rate_limited(db_session, admin):
    device, _code = pairing_service.start_pairing(
        db_session, device_name="My Phone", user_id=admin.id, ttl_minutes=10
    )
    ip = f"10.0.0.{uuid.uuid4().int % 250}"
    for _ in range(3):
        with pytest.raises(pairing_service.PairingError):
            pairing_service.confirm_pairing(
                db_session,
                device_id=device.id,
                submitted_code="BADCODE1",
                ip_address=ip,
                max_attempts_per_minute=3,
            )
    with pytest.raises(pairing_service.RateLimitedError):
        pairing_service.confirm_pairing(
            db_session,
            device_id=device.id,
            submitted_code="BADCODE1",
            ip_address=ip,
            max_attempts_per_minute=3,
        )


def test_revoked_device_cannot_resolve_from_cookie(db_session, admin):
    device, code = pairing_service.start_pairing(
        db_session, device_name="My Phone", user_id=admin.id, ttl_minutes=10
    )
    device, token = pairing_service.confirm_pairing(
        db_session,
        device_id=device.id,
        submitted_code=code,
        ip_address="192.168.1.5",
        max_attempts_per_minute=5,
    )
    secret_key = "test-secret-key"
    cookie_token = pairing_service.issue_device_cookie_token(secret_key, device)
    resolved = pairing_service.resolve_device_from_cookie(
        db_session, secret_key, cookie_token, max_age_seconds=3600
    )
    assert resolved is not None

    pairing_service.revoke_device(db_session, device, user_id=admin.id)
    resolved_after_revoke = pairing_service.resolve_device_from_cookie(
        db_session, secret_key, cookie_token, max_age_seconds=3600
    )
    assert resolved_after_revoke is None
