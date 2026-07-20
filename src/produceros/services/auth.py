"""Single-user local authentication (spec section 19).

Session cookies are signed (itsdangerous) rather than stored server-side,
but logout / "revoke all sessions" still works: a per-user
``session_invalidated_before`` timestamp (kept in AppSetting) rejects any
cookie issued earlier than that moment, which is the same trick used for
JWT-style stateless revocation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.orm import Session

from produceros.models.user import User
from produceros.security import hash_password, verify_password
from produceros.services import settings as settings_service
from produceros.services.audit import log_event

SESSION_COOKIE_NAME = "produceros_session"
CSRF_COOKIE_NAME = "produceros_csrf"
SESSION_SALT = "produceros-session-v1"
LOGIN_LOCKOUT_THRESHOLD = 5
LOGIN_LOCKOUT_SECONDS = 60


class AccountLockedError(Exception):
    pass


def has_any_user(session: Session) -> bool:
    return session.scalar(select(User.id).limit(1)) is not None


def create_first_admin(
    session: Session, *, username: str, password: str, display_name: str
) -> User:
    if has_any_user(session):
        raise ValueError("An administrator account already exists.")
    user = User(
        username=username.strip(),
        password_hash=hash_password(password),
        display_name=display_name.strip() or username.strip(),
        is_admin=True,
    )
    session.add(user)
    session.flush()
    settings_service.mark_first_run_complete(session)
    log_event(
        session,
        event_type="auth.first_run_setup",
        summary=f"Administrator account '{user.username}' created during first-run setup.",
        user_id=user.id,
        entity_type="User",
        entity_id=user.id,
    )
    return user


def authenticate(
    session: Session, *, username: str, password: str, ip_address: str | None = None
) -> User:
    """Verify credentials, enforcing lockout. Raises on any failure."""
    user = session.scalar(select(User).where(User.username == username.strip()))
    now = datetime.now(UTC)

    if user is None:
        log_event(
            session,
            event_type="auth.login_failed",
            summary=f"Login failed for unknown username '{username}'.",
            ip_address=ip_address,
        )
        raise ValueError("Invalid username or password.")

    if user.locked_until and user.locked_until > now:
        log_event(
            session,
            event_type="auth.login_blocked",
            summary=f"Login blocked for '{user.username}': account temporarily locked.",
            user_id=user.id,
            ip_address=ip_address,
        )
        raise AccountLockedError("Too many failed attempts. Try again shortly.")

    if not verify_password(user.password_hash, password):
        user.failed_login_count += 1
        if user.failed_login_count >= LOGIN_LOCKOUT_THRESHOLD:
            user.locked_until = now + timedelta(seconds=LOGIN_LOCKOUT_SECONDS)
        session.flush()
        log_event(
            session,
            event_type="auth.login_failed",
            summary=f"Login failed for '{user.username}': bad password.",
            user_id=user.id,
            ip_address=ip_address,
        )
        raise ValueError("Invalid username or password.")

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    session.flush()
    log_event(
        session,
        event_type="auth.login_success",
        summary=f"'{user.username}' logged in.",
        user_id=user.id,
        ip_address=ip_address,
    )
    return user


def logout(session: Session, user: User, ip_address: str | None = None) -> None:
    invalidate_all_sessions(session, user)
    log_event(
        session,
        event_type="auth.logout",
        summary=f"'{user.username}' logged out.",
        user_id=user.id,
        ip_address=ip_address,
    )


def invalidate_all_sessions(session: Session, user: User) -> None:
    settings_service.set_setting(
        session,
        f"session_invalidated_before:{user.id}",
        datetime.now(UTC).isoformat(),
    )


def _session_invalidated_before(session: Session, user_id: uuid.UUID) -> datetime | None:
    raw = settings_service.get_setting(session, f"session_invalidated_before:{user_id}")
    if not raw:
        return None
    return datetime.fromisoformat(raw)


def issue_session_token(secret_key: str, user: User) -> str:
    serializer = URLSafeTimedSerializer(secret_key, salt=SESSION_SALT)
    return serializer.dumps({"user_id": str(user.id), "issued_at": datetime.now(UTC).isoformat()})


def verify_session_token(
    session: Session, secret_key: str, token: str, max_age_seconds: int
) -> User | None:
    serializer = URLSafeTimedSerializer(secret_key, salt=SESSION_SALT)
    try:
        payload = serializer.loads(token, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None

    try:
        user_id = uuid.UUID(payload["user_id"])
        issued_at = datetime.fromisoformat(payload["issued_at"])
    except (KeyError, ValueError, TypeError):
        return None

    invalidated_before = _session_invalidated_before(session, user_id)
    if invalidated_before and issued_at < invalidated_before:
        return None

    return session.get(User, user_id)
