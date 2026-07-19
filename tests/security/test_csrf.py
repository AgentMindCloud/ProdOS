"""CSRF protection: a POST missing or mismatching the double-submit token
must be rejected even with a valid, logged-in session cookie."""

from __future__ import annotations

from tests.conftest import complete_setup


def test_login_without_csrf_token_is_rejected(client):
    complete_setup(client)
    client.get("/login")  # picks up a csrf cookie
    client.cookies.set("produceros_session", "")  # ensure logged out
    response = client.post(
        "/login",
        data={"username": "producer", "password": "correcthorsebattery"},
    )
    assert response.status_code == 400


def test_login_with_wrong_csrf_token_is_rejected(client):
    complete_setup(client)
    client.get("/login")
    response = client.post(
        "/login",
        data={
            "csrf_token": "not-the-real-token",
            "username": "producer",
            "password": "correcthorsebattery",
        },
    )
    assert response.status_code == 400


def test_login_with_correct_csrf_token_succeeds(client):
    import re

    complete_setup(client)
    client.cookies.delete("produceros_session")
    r = client.get("/login")
    csrf_token = re.search(r'name="csrf_token" value="([^"]+)"', r.text).group(1)
    response = client.post(
        "/login",
        data={"csrf_token": csrf_token, "username": "producer", "password": "correcthorsebattery"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_setup_without_csrf_token_is_rejected(client):
    response = client.post(
        "/setup",
        data={
            "display_name": "Someone",
            "username": "someone",
            "password": "correcthorsebattery",
            "password_confirm": "correcthorsebattery",
        },
    )
    assert response.status_code == 400
