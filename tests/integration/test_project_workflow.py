"""End-to-end project/asset/rights/release workflow, driven through the
real HTTP layer (spec section 25 integration tests)."""

from tests.conftest import complete_setup, get_form_csrf


def test_full_project_to_release_readiness_workflow(client, tmp_path):
    complete_setup(client)

    csrf = get_form_csrf(client, "/artists")
    client.post("/artists/new", data={"csrf_token": csrf, "name": "Integration Artist"})

    csrf = get_form_csrf(client, "/projects/new")
    r = client.post("/projects/new", data={"csrf_token": csrf, "working_title": "Integration Track", "genre": "Techno", "bpm": "128"}, follow_redirects=False)
    assert r.status_code == 303
    project_url = r.headers["location"]

    csrf = get_form_csrf(client, project_url)
    r = client.post(
        f"{project_url}/edit",
        data={
            "csrf_token": csrf, "working_title": "Integration Track", "final_title": "Integration Track (Final)",
            "genre": "Techno", "language": "English", "explicit_status": "clean",
            "master_owner": "Integration Artist", "composition_owner": "Integration Artist",
            "distributor": "Test Distro", "isrc": "US-TST-26-00099",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303

    master_path = tmp_path / "master.wav"
    master_path.write_bytes(b"RIFF" + b"\x00" * 40)  # not a real WAV; registration must not crash on unreadable audio
    csrf = get_form_csrf(client, project_url)
    r = client.post(
        f"{project_url}/assets/register",
        data={"csrf_token": csrf, "asset_type": "master", "file_path": str(master_path), "mark_current": "on"},
        follow_redirects=False,
    )
    assert r.status_code == 303

    csrf = get_form_csrf(client, project_url)
    r = client.post(f"{project_url}/rights-shares/new", data={"csrf_token": csrf, "holder_name": "Integration Artist", "share_type": "master", "percentage": "100", "confirmed": "on"})
    csrf = get_form_csrf(client, project_url)
    r = client.post(f"{project_url}/rights-shares/new", data={"csrf_token": csrf, "holder_name": "Integration Artist", "share_type": "composition", "percentage": "100", "confirmed": "on"})

    project_page = client.get(project_url)
    assert "master.wav" in project_page.text
    assert "100" in project_page.text  # rights percentages rendered

    project_id = project_url.rsplit("/", 1)[-1]
    csrf = get_form_csrf(client, "/releases/new")
    r = client.post("/releases/new", data={"csrf_token": csrf, "project_id": project_id, "title": "Integration Track", "release_type": "streaming_single"}, follow_redirects=False)
    assert r.status_code == 303
    release_url = r.headers["location"]

    release_page = client.get(release_url)
    assert release_page.status_code == 200
    assert "badge" in release_page.text
    # A project this incomplete (no artwork, no release date) must show blocking items.
    assert "badge-blocking" in release_page.text
