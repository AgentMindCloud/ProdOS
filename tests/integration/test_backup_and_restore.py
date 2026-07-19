from produceros.config import get_settings
from produceros.models.enums import BackupType
from produceros.services import catalog as catalog_service
from produceros.services.backup import create_backup, list_backups, restore_backup, restore_dry_run, verify_backup


def test_backup_create_and_verify(db_session, data_dir):
    catalog_service.create_project(db_session, working_title="Backup Me")
    db_session.commit()

    settings = get_settings()
    record = create_backup(db_session, settings, backup_type=BackupType.MANUAL)
    db_session.commit()

    assert record.checksum_sha256
    assert record.size_bytes and record.size_bytes > 0
    ok = verify_backup(db_session, record)
    assert ok
    assert record.verified


def test_backup_history_lists_all_backups(db_session, data_dir):
    settings = get_settings()
    create_backup(db_session, settings)
    create_backup(db_session, settings)
    db_session.commit()
    backups = list_backups(db_session)
    assert len(backups) >= 2


def test_restore_replaces_database_and_makes_pre_restore_backup(db_session, data_dir):
    from sqlalchemy import select

    from produceros.db.session import get_sessionmaker
    from produceros.models.catalog import Project

    settings = get_settings()
    catalog_service.create_project(db_session, working_title="Original Project")
    db_session.commit()
    backup_record = create_backup(db_session, settings)
    db_session.commit()

    # Mutate the live database *after* the backup was taken.
    catalog_service.create_project(db_session, working_title="Added After Backup")
    db_session.commit()

    backups_before_restore = list(settings.backups_dir.glob("pre_restore_*.db"))
    assert backups_before_restore == []

    restore_backup(settings, backup_record.file_path, confirmed=True)

    backups_after_restore = list(settings.backups_dir.glob("pre_restore_*.db"))
    assert len(backups_after_restore) == 1  # safety copy of the pre-restore state was made

    fresh_session = get_sessionmaker()()
    try:
        titles = {p.working_title for p in fresh_session.scalars(select(Project))}
        assert "Original Project" in titles
        assert "Added After Backup" not in titles  # restore rolled back to the backup point
    finally:
        fresh_session.close()


def test_restore_requires_explicit_confirmation(data_dir, db_session):
    settings = get_settings()
    record = create_backup(db_session, settings)
    db_session.commit()
    import pytest

    with pytest.raises(ValueError):
        restore_backup(settings, record.file_path, confirmed=False)


def test_restore_refuses_corrupt_backup(data_dir, db_session, tmp_path):
    settings = get_settings()
    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"not a database")
    import pytest

    with pytest.raises(ValueError):
        restore_backup(settings, corrupt, confirmed=True)
