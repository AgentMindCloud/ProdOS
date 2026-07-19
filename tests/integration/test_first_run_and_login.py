import re

from tests.conftest import complete_setup, get_form_csrf


def test_first_run_redirects_to_setup(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/setup"


def test_setup_creates_account_and_logs_in(client):
    complete_setup(client)
    r = client.get("/")
    assert r.status_code == 200
    assert "Dashboard" in r.text


def test_setup_cannot_run_twice(client):
    complete_setup(client)
    r = client.get("/setup", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/"


def test_login_with_wrong_password_fails(client):
    complete_setup(client)
    client.cookies.clear()
    csrf = get_form_csrf(client, "/login")
    r = client.post("/login", data={"csrf_token": csrf, "username": "producer", "password": "wrong-password"})
    assert r.status_code == 400
    assert "Invalid username or password" in r.text


def test_login_with_correct_password_succeeds(client):
    complete_setup(client)
    client.cookies.clear()
    csrf = get_form_csrf(client, "/login")
    r = client.post("/login", data={"csrf_token": csrf, "username": "producer", "password": "correcthorsebattery"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/"


def test_logout_requires_login_again(client):
    complete_setup(client)
    client.get("/logout")
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/login")


def test_protected_pages_require_login(client):
    for path in ["/projects", "/scanner", "/settings", "/analytics"]:
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 303
        assert r.headers["location"].startswith("/login") or r.headers["location"] == "/setup"
