"""Scanner root management and finding approval workflow."""

from __future__ import annotations

import uuid
from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from produceros.config import get_settings
from produceros.models.enums import FindingStatus, FindingType, ScannerTrigger
from produceros.models.scanner import ScannerFinding, ScannerRoot, ScannerRun
from produceros.scanners.engine import run_scan
from produceros.services.audit import log_event

NEW_VERSION_FINDING_TYPES = {
    FindingType.NEW_FILE,
    FindingType.NEW_MIX_VERSION,
    FindingType.NEW_MASTER_VERSION,
    FindingType.NEW_PROJECT_VERSION,
}


def add_root(session: Session, *, path: str, label: str | None = None) -> ScannerRoot:
    root = ScannerRoot(path=path, label=label, is_active=True)
    session.add(root)
    session.flush()
    return root


def list_roots(session: Session) -> list[ScannerRoot]:
    return list(session.scalars(select(ScannerRoot).order_by(ScannerRoot.path)))


def deactivate_root(session: Session, root: ScannerRoot) -> ScannerRoot:
    root.is_active = False
    session.flush()
    return root


def trigger_scan(
    session: Session,
    *,
    user_id: uuid.UUID | None = None,
    triggered_by: ScannerTrigger = ScannerTrigger.MANUAL,
) -> ScannerRun:
    settings = get_settings()
    roots = list_roots(session)
    run = run_scan(
        session,
        roots=roots,
        allowed_extensions=settings.scanner_allowed_extensions,
        triggered_by=triggered_by,
    )
    log_event(
        session,
        event_type="scanner.run_completed",
        summary=f"Scan completed: {run.files_scanned} files scanned, {run.findings_count} findings.",
        user_id=user_id,
        entity_type="ScannerRun",
        entity_id=run.id,
    )
    return run


def list_findings(
    session: Session, *, run_id: uuid.UUID | None = None, status: FindingStatus | None = None
) -> list[ScannerFinding]:
    stmt = select(ScannerFinding)
    if run_id:
        stmt = stmt.where(ScannerFinding.run_id == run_id)
    if status:
        stmt = stmt.where(ScannerFinding.status == status)
    stmt = stmt.order_by(ScannerFinding.created_at.desc())
    return list(session.scalars(stmt))


def reject_finding(
    session: Session, finding: ScannerFinding, *, user_id: uuid.UUID | None = None
) -> ScannerFinding:
    finding.status = FindingStatus.REJECTED
    from datetime import datetime

    finding.resolved_at = datetime.now(UTC)
    finding.resolved_by = user_id
    session.flush()
    log_event(
        session,
        event_type="scanner.finding_rejected",
        summary=f"Finding for '{finding.path}' rejected.",
        user_id=user_id,
        entity_type="ScannerFinding",
        entity_id=finding.id,
    )
    return finding
