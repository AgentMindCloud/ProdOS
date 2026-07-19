"""FastAPI dependencies: DB session, current user, login/first-run gating."""

from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from produceros.config import Settings, get_settings
from produceros.db.session import get_sessionmaker
from produceros.models.user import User
from produceros.services import auth as auth_service
from produceros.services import pairing as pairing_service
from produceros.services import settings as settings_service


class AuthRedirect(Exception):
    """Raised by ``require_login`` to send the browser to /setup or /login.
    Handled by an exception handler registered in web.app."""

    def __init__(self, location: str) -> None:
        self.location = location


def get_session() -> Generator[Session, None, None]:
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_app_settings() -> Settings:
    return get_settings()


def get_current_user(request: Request, session: Session = Depends(get_session)) -> User | None:
    settings = get_app_settings()
    secret_key = settings.load_or_create_secret_key()

    token = request.cookies.get(auth_service.SESSION_COOKIE_NAME)
    if token:
        user = auth_service.verify_session_token(
            session, secret_key, token, max_age_seconds=settings.session_minutes * 60
        )
        if user is not None:
            return user

    device_token = request.cookies.get(pairing_service.DEVICE_COOKIE_NAME)
    if device_token:
        return pairing_service.resolve_device_from_cookie(
            session, secret_key, device_token, max_age_seconds=pairing_service.SESSION_LIFETIME_DAYS * 86400
        )

    return None


def require_login(request: Request, session: Session = Depends(get_session)) -> User:
    if not auth_service.has_any_user(session):
        raise AuthRedirect("/setup")
    if not settings_service.is_first_run_complete(session):
        raise AuthRedirect("/setup")

    user = get_current_user(request, session)
    if user is None:
        next_param = request.url.path
        raise AuthRedirect(f"/login?next={next_param}")
    return user
