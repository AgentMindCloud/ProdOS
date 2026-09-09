"""Backups must remain distinct and restore must reject unusable schemas."""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from produceros.config import get_settings
from produceros.services import backup, catalog


class FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 9, 0, 0, 0, tzinfo=UTC)


def test_two_backups_in_same_clock_tick_preserve_both_snapshots(db_session, monkeypatch):
    monkeypatch.setattr(backup, "datetime", FrozenDateTime)
    settings = get_settings()
    first = backup.create_backup(db_session, settings)
    db_session.commit()
    first_bytes = Path(first.file_path).read_bytes()

    catalog.create_project(db_session, working_title="Added after first backup")
    db_session.commit()
    second = backup.create_backup(db_session, settings)
    db_session.commit()

    assert first.file_path != second.file_path
    assert Path(first.file_path).read_bytes() == first_bytes
    assert backup.verify_backup(db_session, first)
    assert backup.verify_backup(db_session, second)


@pytest.mark.parametrize("schema", ["", "CREATE TABLE unrelated (value TEXT)"])
def test_valid_sqlite_without_produceros_schema_cannot_replace_live_database(
    db_session, tmp_path, schema
):
    settings = get_settings()
    catalog.create_project(db_session, working_title="Keep this project")
    db_session.commit()
    candidate = tmp_path / "unrelated.db"
    connection = sqlite3.connect(candidate)
    try:
        if schema:
            connection.execute(schema)
        connection.commit()
    finally:
        connection.close()
    before = settings.database_path.read_bytes()

    dry_run = backup.restore_dry_run(candidate)
    assert not dry_run.ok
    assert dry_run.warnings
    with pytest.raises(ValueError, match="validation failed"):
        backup.restore_backup(settings, candidate, confirmed=True)

    assert settings.database_path.read_bytes() == before
    assert not list(settings.backups_dir.glob("pre_restore_*.db"))


def test_restore_rejects_missing_required_column(db_session):
    settings = get_settings()
    record = backup.create_backup(db_session, settings)
    db_session.commit()
    connection = sqlite3.connect(record.file_path)
    try:
        connection.execute("ALTER TABLE projects RENAME COLUMN working_title TO obsolete_title")
        connection.commit()
    finally:
        connection.close()

    dry_run = backup.restore_dry_run(record.file_path)
    assert not dry_run.ok
    assert any("working_title" in warning for warning in dry_run.warnings)


def test_restore_dry_run_rejects_directory(tmp_path):
    assert not backup.restore_dry_run(tmp_path).ok
