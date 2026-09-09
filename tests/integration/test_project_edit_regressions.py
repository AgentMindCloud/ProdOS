"""Edits must preserve existing metadata and allow explicit reversals."""

import re

from tests.conftest import complete_setup, get_form_csrf


def test_edit_form_preserves_tags_and_can_unconfirm_splits(client):
    complete_setup(client)
    response = client.post(
        "/projects/new",
        data={"csrf_token": get_form_csrf(client, "/projects/new"), "working_title": "Test song"},
    )
    path = response.url.path
    token = get_form_csrf(client, path)
    client.post(
        f"{path}/edit",
        data={"csrf_token": token, "tags": "summer, driving", "split_confirmed": "on"},
    )
    html = client.get(path).text
    tags = re.search(r'name="tags"[^>]*value="([^"]*)"', html)
    assert tags and set(tags.group(1).split(", ")) == {"summer", "driving"}
    assert re.search(r'id="split_confirmed"[^>]*checked', html)
    # Browsers omit unchecked checkboxes; this marker identifies a complete form.
    client.post(
        f"{path}/edit",
        data={"csrf_token": token, "split_confirmed_present": "1", "tags": "summer, driving"},
    )
    html = client.get(path).text
    assert not re.search(r'id="split_confirmed"[^>]*checked', html)
    tags = re.search(r'name="tags"[^>]*value="([^"]*)"', html)
    assert tags and set(tags.group(1).split(", ")) == {"summer", "driving"}


def test_unknown_project_is_a_not_found_response(client):
    complete_setup(client)
    assert client.get("/projects/00000000-0000-0000-0000-000000000000").status_code == 404
    assert client.get("/projects/not-a-project").status_code == 404
