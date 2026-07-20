"""Brute-force lockout and session invalidation, exercised over real HTTP."""

from __future__ import annotations

import re

from tests.conftest import complete_setup


def _login_csrf(client) -> str:
    r = client.get("/login")
    return re.search(r'name="csrf_token" value="([^"]+)"', r.text).group(1)


def test_five_failed_logins_lock_the_account(client):
    complete_setup(client)
    client.cookies.delete("produceros_session")

    for _ in range(5):
        csrf_token = _login_csrf(client)
        response = client.post(
            "/login",
            data={"csrf_token": csrf_token, "username": "producer", "password": "wrong-password"},
        )
        assert response.status_code == 400

    csrf_token = _login_csrf(client)
    locked_response = client.post(
        "/login",
        data={"csrf_token": csrf_token, "username": "producer", "password": "correcthorsebattery"},
    )
    assert locked_response.status_code == 429


def test_logout_invalidates_the_session_cookie(client):
    complete_setup(client)
    dashboard = client.get("/")
    assert dashboard.status_code == 200

    client.get("/logout")

    still_using_old_cookie = client.get("/", follow_redirects=False)
    assert still_using_old_cookie.status_code in (302, 303)
    assert still_using_old_cookie.headers["location"].startswith("/login")


def test_reusing_a_cookie_issued_before_invalidation_fails(client, db_session, admin_user):
    from produceros.config import get_settings
    from produceros.services import auth as auth_service

    settings = get_settings()
    secret_key = settings.load_or_create_secret_key()
    token = auth_service.issue_session_token(secret_key, admin_user)

    user = auth_service.verify_session_token(db_session, secret_key, token, max_age_seconds=3600)
    assert user is not None

    auth_service.invalidate_all_sessions(db_session, admin_user)
    db_session.commit()

    user_after = auth_service.verify_session_token(
        db_session, secret_key, token, max_age_seconds=3600
    )
    assert user_after is None
