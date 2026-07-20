"""The read-only filesystem scanner (spec section 9).

The scanner never deletes, renames, moves, replaces, or uploads. It only
*observes* configured roots and records findings; turning a finding into a
real file operation always goes through
``produceros.services.file_operations`` and an explicit approval.

Each run is independent and safe to re-run (a scan is never resumed
mid-walk; if interrupted, the ``ScannerRun`` is marked ``failed`` and the
user simply starts a new one -- this is the "safely restartable" behavior
required by spec section 29, chosen over checkpoint/resume complexity that
isn't justified for typical producer folder sizes).
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from produceros.models.assets import AssetVersion
from produceros.models.enums import FindingType, ScannerRunStatus, ScannerTrigger
from produceros.models.scanner import ScannerFinding, ScannerRoot, ScannerRun
from produceros.scanners.filename_parser import parse_filename
from produceros.scanners.hashing import hash_file
from produceros.security import (
    PathSecurityError,
    is_allowed_extension,
    resolve_within_allowed_roots,
)


def run_scan(
    session: Session,
    *,
    roots: list[ScannerRoot],
    allowed_extensions: list[str],
    triggered_by: ScannerTrigger = ScannerTrigger.MANUAL,
) -> ScannerRun:
    active_roots = [r for r in roots if r.is_active]
    run = ScannerRun(
        started_at=datetime.now(UTC),
        status=ScannerRunStatus.RUNNING,
        scanned_roots=[r.path for r in active_roots],
        dry_run=True,
        triggered_by=triggered_by,
    )
    session.add(run)
    session.flush()

    root_paths = [r.path for r in active_roots]
    files_scanned = 0
    findings_count = 0
    seen_paths: set[str] = set()

    try:
        for root in active_roots:
            root_path = Path(root.path)
            if not root_path.exists() or not root_path.is_dir():
                _add_finding(
                    session,
                    run,
                    FindingType.INVALID_PATH,
                    root.path,
                    detail="Configured scanner root does not exist or is not a directory.",
                )
                findings_count += 1
                continue

            for current_dir, _dirs, files in os.walk(root_path, onerror=lambda e: None):
                for name in files:
                    candidate = Path(current_dir) / name
                    files_scanned += 1

                    try:
                        resolved = resolve_within_allowed_roots(candidate, root_paths)
                    except PathSecurityError:
                        _add_finding(
                            session,
                            run,
                            FindingType.OUTSIDE_ROOT,
                            str(candidate),
                            detail="File resolved outside all approved scanner roots.",
                        )
                        findings_count += 1
                        continue

                    seen_paths.add(str(resolved))

                    if not is_allowed_extension(resolved, allowed_extensions):
                        _add_finding(
                            session,
                            run,
                            FindingType.UNEXPECTED_FILE,
                            str(resolved),
                            detail=f"Extension '{resolved.suffix}' is not in the allowlist.",
                        )
                        findings_count += 1
                        continue

                    try:
                        stat = resolved.stat()
                    except OSError as exc:
                        _add_finding(
                            session,
                            run,
                            FindingType.LOCKED_FILE,
                            str(resolved),
                            detail=f"File could not be read: {exc}",
                        )
                        findings_count += 1
                        continue

                    try:
                        content_hash = hash_file(resolved)
                    except OSError as exc:
                        _add_finding(
                            session,
                            run,
                            FindingType.LOCKED_FILE,
                            str(resolved),
                            detail=f"File is locked or unavailable: {exc}",
                        )
                        findings_count += 1
                        continue

                    finding_type = _classify(session, resolved, content_hash, stat.st_size)
                    if finding_type is not None:
                        _add_finding(
                            session,
                            run,
                            finding_type,
                            str(resolved),
                            content_hash=content_hash,
                            size_bytes=stat.st_size,
                            detail=_detail_for(finding_type, resolved),
                        )
                        findings_count += 1

        _check_missing_files(session, run, root_paths, seen_paths)
        findings_count = (
            session.scalar(
                select(func.count())
                .select_from(ScannerFinding)
                .where(ScannerFinding.run_id == run.id)
            )
            or 0
        )

        run.status = ScannerRunStatus.COMPLETED
        run.completed_at = datetime.now(UTC)
        run.files_scanned = files_scanned
        run.findings_count = findings_count or 0
    except Exception as exc:  # pragma: no cover - defensive top-level guard
        run.status = ScannerRunStatus.FAILED
        run.error_message = str(exc)
        run.completed_at = datetime.now(UTC)
        run.files_scanned = files_scanned
        raise
    finally:
        session.flush()

    return run


def _classify(
    session: Session, path: Path, content_hash: str, size_bytes: int
) -> FindingType | None:
    existing_by_path = session.scalar(
        select(AssetVersion).where(AssetVersion.full_path == str(path))
    )
    if existing_by_path is not None:
        if existing_by_path.content_hash and existing_by_path.content_hash != content_hash:
            return FindingType.CHANGED_FILE
        return None  # already registered and unchanged

    exact_duplicate = session.scalar(
        select(AssetVersion).where(AssetVersion.content_hash == content_hash)
    )
    if exact_duplicate is not None:
        return FindingType.EXACT_DUPLICATE

    possible_duplicate = session.scalar(
        select(AssetVersion).where(
            AssetVersion.original_filename == path.name,
            AssetVersion.size_bytes == size_bytes,
        )
    )
    if possible_duplicate is not None:
        return FindingType.POSSIBLE_DUPLICATE

    parsed = parse_filename(path.name)
    if parsed.asset_hint == "fl_project" or path.suffix.lower() == ".flp":
        return FindingType.NEW_PROJECT_VERSION
    if parsed.mix_or_master == "mix":
        return FindingType.NEW_MIX_VERSION
    if parsed.mix_or_master == "master":
        return FindingType.NEW_MASTER_VERSION
    return FindingType.NEW_FILE


def _detail_for(finding_type: FindingType, path: Path) -> str:
    messages = {
        FindingType.CHANGED_FILE: f"'{path.name}' content differs from the registered version.",
        FindingType.EXACT_DUPLICATE: f"'{path.name}' is byte-identical to an already-registered file.",
        FindingType.POSSIBLE_DUPLICATE: f"'{path.name}' matches filename+size of an existing version; verify manually.",
        FindingType.NEW_PROJECT_VERSION: f"'{path.name}' looks like a new FL Studio project checkpoint.",
        FindingType.NEW_MIX_VERSION: f"'{path.name}' looks like a new mix version.",
        FindingType.NEW_MASTER_VERSION: f"'{path.name}' looks like a new master version.",
        FindingType.NEW_FILE: f"'{path.name}' is not yet registered in ProducerOS.",
    }
    return messages.get(finding_type, f"Finding for '{path.name}'.")


def _check_missing_files(
    session: Session, run: ScannerRun, root_paths: list[str], seen_paths: set[str]
) -> None:
    registered = session.scalars(select(AssetVersion).where(AssetVersion.is_current.is_(True)))
    for version in registered:
        try:
            resolved = resolve_within_allowed_roots(version.full_path, root_paths)
        except PathSecurityError:
            continue  # not under a root we scanned this run
        if str(resolved) not in seen_paths:
            _add_finding(
                session,
                run,
                FindingType.MISSING_FILE,
                version.full_path,
                related_asset_version_id=version.id,
                detail=f"Registered file '{version.original_filename}' was not found during this scan.",
            )


def _add_finding(
    session: Session,
    run: ScannerRun,
    finding_type: FindingType,
    path: str,
    *,
    content_hash: str | None = None,
    size_bytes: int | None = None,
    detail: str | None = None,
    related_asset_version_id=None,
) -> ScannerFinding:
    finding = ScannerFinding(
        run_id=run.id,
        finding_type=finding_type,
        path=path,
        content_hash=content_hash,
        size_bytes=size_bytes,
        detail=detail,
        related_asset_version_id=related_asset_version_id,
    )
    session.add(finding)
    session.flush()
    return finding
