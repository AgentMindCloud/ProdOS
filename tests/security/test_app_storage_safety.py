"""App-owned storage must not overwrite unrelated files through aliases/collisions."""

import sqlite3
from pathlib import Path

import pytest

from produceros.config import Settings
from produceros.services import backup


def test_restore_preserves_preexisting_staging_filename(tmp_path):
    source = tmp_path / "backup.db"
    destination = tmp_path / "produceros.db"
    old_staging = tmp_path / "produceros.db.restore-staged"
    source.write_bytes(b"restored app database")
    destination.write_bytes(b"old app database")
    old_staging.write_bytes(b"unrelated user file")

    backup._swap_in_database(source, destination)

    assert destination.read_bytes() == b"restored app database"
    assert old_staging.read_bytes() == b"unrelated user file"
    assert source.read_bytes() == b"restored app database"


def test_key_creation_never_overwrites_a_file_created_in_the_meantime(tmp_path, monkeypatch):
    settings = Settings(data_dir=tmp_path / "app")

    def concurrent_creation(_length):
        settings.secret_key_path.write_text("keep-existing-key", encoding="utf-8")
        return "new-key-must-not-overwrite"

    monkeypatch.setattr("produceros.config.secrets.token_urlsafe", concurrent_creation)
    with pytest.raises(FileExistsError):
        settings.load_or_create_secret_key()
    assert settings.secret_key_path.read_text() == "keep-existing-key"


def test_writable_database_hardlink_cannot_modify_user_file(tmp_path):
    settings = Settings(data_dir=tmp_path / "app")
    settings.data_dir.mkdir()
    original = tmp_path / "original.wav"
    original.write_bytes(b"keep original music")
    settings.database_path.hardlink_to(original)

    with pytest.raises(ValueError, match="linked"):
        settings.ensure_directories()
    assert original.read_bytes() == b"keep original music"


def test_app_directory_symlink_is_refused_before_creating_files(tmp_path):
    original = tmp_path / "Music"
    original.mkdir()
    alias = tmp_path / "app"
    try:
        alias.symlink_to(original, target_is_directory=True)
    except OSError:
        pytest.skip("This account cannot create directory symlinks.")
    settings = Settings(data_dir=alias)

    with pytest.raises(ValueError, match="linked"):
        settings.ensure_directories()
    assert list(original.iterdir()) == []


def test_storage_validation_refuses_path_outside_app_directory(tmp_path):
    settings = Settings(data_dir=tmp_path / "app")
    with pytest.raises(ValueError, match="outside"):
        settings.validate_owned_path(tmp_path / "Music" / "track.wav")


def test_new_backup_does_not_overwrite_an_existing_uuid_collision(db_session, monkeypatch):
    from produceros.config import get_settings

    settings = get_settings()
    first = backup.create_backup(db_session, settings)
    db_session.commit()
    existing = Path(first.file_path)
    before = existing.read_bytes()
    monkeypatch.setattr(backup, "_new_snapshot_path", lambda *_args: existing)

    with pytest.raises(FileExistsError):
        backup.create_backup(db_session, settings)
    assert existing.read_bytes() == before


def test_external_backup_validation_preserves_existing_sqlite_sidecars(tmp_path):
    candidate = tmp_path / "candidate.db"
    with sqlite3.connect(candidate) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE unrelated (value TEXT)")
        connection.commit()
    connection.close()
    sidecar = Path(str(candidate) + "-shm")
    sidecar.write_bytes(b"USER-SIDECAR-SENTINEL")
    before = candidate.read_bytes()

    assert not backup.restore_dry_run(candidate).ok

    assert candidate.read_bytes() == before
    assert sidecar.read_bytes() == b"USER-SIDECAR-SENTINEL"
    assert not Path(str(candidate) + "-wal").exists()


def test_backup_with_pending_wal_is_rejected_without_touching_files(tmp_path):
    candidate = tmp_path / "candidate.db"
    candidate.write_bytes(b"must stay unchanged")
    wal = Path(str(candidate) + "-wal")
    wal.write_bytes(b"pending data")

    result = backup.restore_dry_run(candidate)

    assert not result.ok
    assert "standalone" in " ".join(result.warnings).lower()
    assert candidate.read_bytes() == b"must stay unchanged"
    assert wal.read_bytes() == b"pending data"
