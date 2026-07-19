import sqlite3

from produceros.services.backup import restore_dry_run


def test_restore_dry_run_on_valid_database(data_dir, db_session):
    from produceros.config import get_settings

    settings = get_settings()
    backup_path = data_dir / "manual_backup.db"
    data_dir.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(str(settings.database_path))
    dest = sqlite3.connect(str(backup_path))
    source.backup(dest)
    dest.close()
    source.close()

    result = restore_dry_run(backup_path)
    assert result.ok
    assert result.integrity_check == "ok"
    assert "projects" in result.table_counts


def test_restore_dry_run_on_missing_file(tmp_path):
    result = restore_dry_run(tmp_path / "does_not_exist.db")
    assert not result.ok
    assert result.warnings


def test_restore_dry_run_on_corrupt_file(tmp_path):
    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"this is not a sqlite database" * 20)
    result = restore_dry_run(corrupt)
    assert not result.ok
