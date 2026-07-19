"""Pairing-code confirmation is rate-limited at the HTTP boundary, not just
in the service layer -- an attacker hitting /lan/pair/{id}/confirm directly
must still be throttled."""

from __future__ import annotations

import re

from tests.conftest import complete_setup


def _pair_csrf(client, device_id: str) -> str:
    r = client.get(f"/lan/pair/{device_id}")
    return re.search(r'name="csrf_token" value="([^"]+)"', r.text).group(1)


def test_repeated_wrong_pairing_codes_are_rate_limited_over_http(client, monkeypatch):
    from produceros.config import reset_settings_cache

    monkeypatch.setenv("PRODUCEROS_BIND_MODE", "lan")
    reset_settings_cache()

    complete_setup(client)

    csrf_token = re.search(
        r'name="csrf_token" value="([^"]+)"', client.get("/settings/lan").text
    ).group(1)
    start_response = client.post(
        "/settings/lan/start", data={"csrf_token": csrf_token, "device_name": "Test Phone"}
    )
    assert start_response.status_code == 200
    device_id = re.search(r"/lan/pair/([0-9a-fA-F-]{36})", start_response.text).group(1)

    statuses = []
    for _ in range(6):
        pair_csrf = _pair_csrf(client, device_id)
        response = client.post(
            f"/lan/pair/{device_id}/confirm",
            data={"csrf_token": pair_csrf, "code": "WRONGCD"},
        )
        statuses.append(response.status_code)

    assert 429 in statuses
