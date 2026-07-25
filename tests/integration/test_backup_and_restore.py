from produceros.config import get_settings
from produceros.models.enums import BackupType
from produceros.services import catalog as catalog_service
from produceros.services.backup import (
    create_backup,
    list_backups,
    restore_backup,
    verify_backup,
)


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


def test_restore_leaves_no_staging_file_behind(db_session, data_dir):
    """The restore swaps a staged copy into place rather than writing over
    the live database directly (Windows refuses the latter while any handle
    is open). The staging file must never survive the operation."""
    settings = get_settings()
    catalog_service.create_project(db_session, working_title="Staging Check")
    db_session.commit()
    record = create_backup(db_session, settings)
    db_session.commit()

    restore_backup(settings, record.file_path, confirmed=True)

    staged = settings.database_path.with_name(settings.database_path.name + ".restore-staged")
    assert not staged.exists()
    assert settings.database_path.exists()


def test_restore_through_the_web_ui_succeeds_with_a_live_session(client):
    """Exercises restore through the real HTTP route, which used to hold its
    own open database session while the file was replaced underneath it.

    Note on what this can and cannot prove: the failure that motivated the
    fix is Windows-only (an open handle blocks replacing a file; POSIX
    happily lets it through), so running here on Linux this test cannot
    reproduce the original breakage. It guards the surrounding behavior --
    the route completes, and the app still works against the restored
    database -- while the Windows-specific part is covered by construction
    (session closed before the swap, staged os.replace in
    services/backup._swap_in_database) rather than by this assertion."""
    import re

    from tests.conftest import complete_setup

    complete_setup(client)

    created = client.post(
        "/backup/create",
        data={
            "csrf_token": re.search(
                r'name="csrf_token" value="([^"]+)"', client.get("/backup").text
            ).group(1)
        },
        follow_redirects=True,
    )
    assert created.status_code == 200

    page = client.get("/backup").text
    backup_id = re.search(r"/backup/([0-9a-f-]{36})/restore-confirm", page).group(1)
    csrf_token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)

    response = client.post(
        f"/backup/{backup_id}/restore-confirm",
        data={"csrf_token": csrf_token, "confirm": "yes"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    # The app must still be usable against the restored database.
    assert client.get("/backup").status_code == 200
