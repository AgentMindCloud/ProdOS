"""Backup, restore, and data-portability (spec section 20).

Audio files are never included in a backup -- only their paths and
hashes (via the audio-manifest export), since the database itself only
ever stores references to files on disk. Backups use SQLite's native
online-backup API so an in-progress WAL write never corrupts the copy.
"""

from __future__ import annotations

import hashlib
import shutil
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from produceros.config import Settings
from produceros.models import Base
from produceros.models.assets import AssetVersion
from produceros.models.enums import BackupType
from produceros.models.system import BackupRecord
from produceros.services.audit import log_event

CHUNK_SIZE = 1024 * 1024


def _sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def create_backup(
    session: Session,
    settings: Settings,
    *,
    backup_type: BackupType = BackupType.MANUAL,
    user_id: uuid.UUID | None = None,
) -> BackupRecord:
    settings.backups_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = settings.backups_dir / f"produceros_{timestamp}.db"

    source_conn = sqlite3.connect(str(settings.database_path))
    try:
        dest_conn = sqlite3.connect(str(destination))
        try:
            source_conn.backup(dest_conn)
        finally:
            dest_conn.close()
    finally:
        source_conn.close()

    checksum = _sha256_of_file(destination)
    record = BackupRecord(
        backup_type=backup_type,
        file_path=str(destination),
        size_bytes=destination.stat().st_size,
        checksum_sha256=checksum,
        verified=False,
    )
    session.add(record)
    session.flush()
    log_event(
        session,
        event_type="backup.created",
        summary=f"Backup created at '{destination.name}' ({record.size_bytes} bytes).",
        user_id=user_id,
        entity_type="BackupRecord",
        entity_id=record.id,
    )
    return record


def verify_backup(
    session: Session, record: BackupRecord, *, user_id: uuid.UUID | None = None
) -> bool:
    path = Path(record.file_path)
    ok = path.exists()
    if ok:
        current_checksum = _sha256_of_file(path)
        ok = current_checksum == record.checksum_sha256
        if ok:
            conn = sqlite3.connect(str(path))
            try:
                result = conn.execute("PRAGMA integrity_check").fetchone()
                ok = result is not None and result[0] == "ok"
            finally:
                conn.close()

    record.verified = ok
    record.verified_at = datetime.now(UTC)
    session.flush()
    log_event(
        session,
        event_type="backup.verified",
        summary=f"Backup '{path.name}' verification: {'passed' if ok else 'FAILED'}.",
        user_id=user_id,
        entity_type="BackupRecord",
        entity_id=record.id,
    )
    return ok


def list_backups(session: Session) -> list[BackupRecord]:
    return list(session.scalars(select(BackupRecord).order_by(BackupRecord.created_at.desc())))


@dataclass
class RestoreDryRunResult:
    ok: bool
    integrity_check: str
    table_counts: dict[str, int]
    warnings: list[str]


def restore_dry_run(backup_path: str | Path) -> RestoreDryRunResult:
    path = Path(backup_path)
    warnings: list[str] = []
    if not path.exists():
        return RestoreDryRunResult(
            ok=False,
            integrity_check="file not found",
            table_counts={},
            warnings=[f"'{path}' does not exist."],
        )

    conn = sqlite3.connect(str(path))
    try:
        try:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()
            integrity_result = integrity[0] if integrity else "unknown"
        except sqlite3.DatabaseError as exc:
            return RestoreDryRunResult(
                ok=False,
                integrity_check="not a valid SQLite database",
                table_counts={},
                warnings=[f"'{path}' is not a valid SQLite database: {exc}"],
            )

        table_counts: dict[str, int] = {}
        for table_name in Base.metadata.tables:
            try:
                # table_name is our own ORM metadata (Base.metadata.tables), never user input.
                count = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()  # noqa: S608 # nosec B608
                table_counts[table_name] = count[0] if count else 0
            except sqlite3.OperationalError:
                warnings.append(
                    f"Table '{table_name}' missing from backup (may be an older schema version)."
                )
    finally:
        conn.close()

    ok = integrity_result == "ok"
    return RestoreDryRunResult(
        ok=ok, integrity_check=integrity_result, table_counts=table_counts, warnings=warnings
    )


def restore_backup(
    settings: Settings,
    backup_path: str | Path,
    *,
    confirmed: bool,
) -> Path:
    """Replace the live database with ``backup_path``. Requires explicit
    ``confirmed=True``. The current live database is itself backed up
    first (BackupType.PRE_RESTORE) so a restore can always be undone."""
    if not confirmed:
        raise ValueError("Restore requires explicit confirmation.")

    dry_run = restore_dry_run(backup_path)
    if not dry_run.ok:
        raise ValueError(
            f"Refusing to restore: backup failed integrity check ({dry_run.integrity_check})."
        )

    from produceros.db.session import reset_engine_cache

    settings.backups_dir.mkdir(parents=True, exist_ok=True)
    if settings.database_path.exists():
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        pre_restore_path = settings.backups_dir / f"pre_restore_{timestamp}.db"
        source_conn = sqlite3.connect(str(settings.database_path))
        try:
            dest_conn = sqlite3.connect(str(pre_restore_path))
            try:
                source_conn.backup(dest_conn)
            finally:
                dest_conn.close()
        finally:
            source_conn.close()

    reset_engine_cache()
    shutil.copy2(Path(backup_path), settings.database_path)
    for suffix in ("-wal", "-shm"):
        stale = Path(str(settings.database_path) + suffix)
        if stale.exists():
            stale.unlink()

    return settings.database_path


def _row_to_dict(instance) -> dict:
    mapper = inspect(instance).mapper
    result = {}
    for column in mapper.columns:
        value = getattr(instance, column.key)
        if isinstance(value, uuid.UUID):
            value = str(value)
        elif isinstance(value, datetime) or hasattr(value, "isoformat"):
            value = value.isoformat()
        result[column.key] = value
    return result


def export_metadata_json(session: Session) -> dict:
    """Export all catalog/metadata tables as plain JSON-serializable data.
    Never includes audio bytes (the schema never stores any)."""
    export: dict[str, list[dict]] = {}
    for table_name, table in Base.metadata.tables.items():
        model = next(
            (m.class_ for m in Base.registry.mappers if m.local_table is table),
            None,
        )
        if model is None:
            continue
        rows = session.scalars(select(model)).all()
        export[table_name] = [_row_to_dict(r) for r in rows]
    return export


def rows_to_csv(rows: list[dict]) -> str:
    """Generic dict-list -> CSV serializer, used for the "export as CSV
    where appropriate" pieces of spec section 20 (project catalog,
    checklist results, delivery manifests)."""
    import csv
    import io

    if not rows:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def export_audio_manifest(session: Session) -> list[dict]:
    """Optional manifest of external audio paths + hashes, so a producer
    can verify/relocate audio assets after moving ProducerOS to a new
    computer (spec section 20)."""
    manifest = []
    versions = session.scalars(select(AssetVersion)).all()
    for version in versions:
        manifest.append(
            {
                "asset_version_id": str(version.id),
                "original_filename": version.original_filename,
                "full_path": version.full_path,
                "content_hash": version.content_hash,
                "size_bytes": version.size_bytes,
                "is_current": version.is_current,
            }
        )
    return manifest
