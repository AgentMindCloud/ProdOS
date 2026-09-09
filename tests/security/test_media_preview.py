"""Real HTTP coverage for the local-media read boundary."""

from __future__ import annotations

import uuid
from pathlib import Path

import anyio
import pytest

from produceros.models.assets import Asset, AssetVersion
from produceros.models.catalog import Project
from produceros.models.enums import AssetType
from produceros.models.scanner import ScannerRoot
from produceros.services.media import project_media
from tests.conftest import complete_setup


def _register(db_session, path, *, root=None, asset_type=AssetType.MIX):
    project = Project(
        internal_code=f"MEDIA-{uuid.uuid4().hex[:12]}",
        working_title="Preview test",
        project_root_path=str(root) if root else None,
    )
    db_session.add(project)
    db_session.flush()
    asset = Asset(project_id=project.id, asset_type=asset_type, label="Preview")
    db_session.add(asset)
    db_session.flush()
    version = AssetVersion(
        asset_id=asset.id,
        version_number=1,
        original_filename=path.name,
        full_path=str(path),
        is_current=True,
    )
    db_session.add(version)
    db_session.commit()
    return project, version


def _url(version):
    return f"/asset-versions/{version.id}/preview"


def test_preview_requires_login(client, db_session, tmp_path):
    complete_setup(client)
    path = tmp_path / "master.wav"
    path.write_bytes(b"RIFF" + bytes(100))
    _, version = _register(db_session, path, root=tmp_path)
    client.cookies.clear()

    response = client.get(_url(version), follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")
    assert path.name not in response.text


def test_audio_range_uses_file_response_and_bounded_reads(
    client, db_session, tmp_path, monkeypatch
):
    complete_setup(client)
    path = tmp_path / "master.wav"
    payload = bytes(range(256)) * 8192
    path.write_bytes(payload)
    before = path.stat().st_mtime_ns
    project, version = _register(db_session, path, root=tmp_path)
    reads = []
    original_read = anyio.AsyncFile.read

    async def bounded_read(file, size=-1):
        assert 0 < size <= 64 * 1024, "Media reads must stay bounded, even for large files"
        reads.append(size)
        return await original_read(file, size)

    monkeypatch.setattr(anyio.AsyncFile, "read", bounded_read)
    response = client.get(_url(version), headers={"Range": "bytes=100-199"})

    assert response.status_code == 206
    assert response.content == payload[100:200]
    assert response.headers["content-range"] == f"bytes 100-199/{len(payload)}"
    assert response.headers["content-type"] == "audio/wav"
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert reads == [100]
    assert project_media(db_session, project)["audio"].id == version.id

    reads.clear()
    full_response = client.get(_url(version))
    assert full_response.status_code == 200
    assert full_response.content == payload
    assert len(reads) > 1
    assert path.stat().st_mtime_ns == before


def test_missing_files_and_versions_return_generic_404(client, db_session, tmp_path):
    complete_setup(client)
    project, version = _register(db_session, tmp_path / "missing.wav", root=tmp_path)

    for url in (_url(version), f"/asset-versions/{uuid.uuid4()}/preview"):
        response = client.get(url)
        assert response.status_code == 404
        assert response.json() == {"detail": "Preview unavailable."}
        assert str(tmp_path) not in response.text
    assert project_media(db_session, project) == {"audio": None, "artwork": None}


@pytest.mark.parametrize("suffix", [".flp", ".svg", ".html", ".pdf", ".txt", ".zip"])
def test_unsupported_formats_are_never_served(client, db_session, tmp_path, suffix):
    complete_setup(client)
    path = tmp_path / f"private{suffix}"
    path.write_bytes(b"Never preview this file")
    project, version = _register(db_session, path, root=tmp_path, asset_type=AssetType.ARTWORK)

    assert client.get(_url(version)).status_code == 404
    assert project_media(db_session, project) == {"audio": None, "artwork": None}


@pytest.mark.parametrize("root_kind", ["unset", "outside", "inactive", "app_data", "relative"])
def test_unapproved_roots_fail_closed(client, db_session, tmp_path, data_dir, root_kind):
    complete_setup(client)
    path = (data_dir if root_kind == "app_data" else tmp_path) / "private.wav"
    path.write_bytes(b"RIFF" + bytes(100))
    root = {
        "unset": None,
        "outside": tmp_path / "elsewhere",
        "inactive": None,
        "app_data": tmp_path,
        "relative": Path("."),
    }[root_kind]
    project, version = _register(db_session, path, root=root)
    if root_kind == "inactive":
        db_session.add(ScannerRoot(path=str(tmp_path), is_active=False))
        db_session.commit()

    assert client.get(_url(version)).status_code == 404
    assert project_media(db_session, project)["audio"] is None


def test_active_scanner_root_allows_registered_media(client, db_session, tmp_path):
    complete_setup(client)
    path = tmp_path / "registered.wav"
    path.write_bytes(b"RIFF" + bytes(100))
    _, version = _register(db_session, path)
    db_session.add(ScannerRoot(path=str(tmp_path), is_active=True))
    db_session.commit()

    assert client.get(_url(version)).status_code == 200


def test_current_artwork_is_available_as_a_raster_image(client, db_session, tmp_path):
    complete_setup(client)
    path = tmp_path / "cover.png"
    # The file response preserves bytes; browser decoding is separate.
    payload = b"\x89PNG\r\n\x1a\n" + bytes(64)
    path.write_bytes(payload)
    project, version = _register(db_session, path, root=tmp_path, asset_type=AssetType.ARTWORK)

    response = client.get(_url(version))
    assert response.status_code == 200
    assert response.content == payload
    assert response.headers["content-type"] == "image/png"
    assert project_media(db_session, project) == {"audio": None, "artwork": version}


def test_project_pointers_cannot_select_another_projects_media(db_session, tmp_path):
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"RIFF" + bytes(100))
    project, own_version = _register(db_session, audio, root=tmp_path)
    _, other_version = _register(db_session, audio, root=tmp_path)
    own_version.is_current = False
    project.current_master_asset_version_id = other_version.id
    project.current_mix_asset_version_id = other_version.id
    project.artwork_asset_version_id = other_version.id
    db_session.commit()

    assert project_media(db_session, project) == {"audio": None, "artwork": None}


def test_symlink_escape_is_rejected(client, db_session, tmp_path):
    complete_setup(client)
    root = tmp_path / "music"
    root.mkdir()
    outside = tmp_path / "outside.wav"
    outside.write_bytes(b"RIFF" + bytes(100))
    link = root / "escape.wav"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("This Windows account cannot create symlinks")
    project, version = _register(db_session, link, root=root)

    assert client.get(_url(version)).status_code == 404
    assert project_media(db_session, project)["audio"] is None
