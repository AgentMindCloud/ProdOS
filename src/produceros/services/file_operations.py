"""Approved, audited file operations (spec sections 2 and 9).

ProducerOS never deletes, renames, moves, or replaces a file on disk on
its own initiative. Every operation is proposed as a dry run, requires an
explicit approval, and is logged before and after execution.
"""

from __future__ import annotations

import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from produceros.models.enums import FileOperationStatus, FileOperationType
from produceros.models.scanner import ApprovedFileOperation
from produceros.security import PathSecurityError, resolve_within_allowed_roots
from produceros.services.audit import log_event


def propose_operation(
    session: Session,
    *,
    operation_type: FileOperationType,
    source_path: str,
    destination_path: str | None = None,
    requested_by: uuid.UUID | None = None,
    finding_id: uuid.UUID | None = None,
) -> ApprovedFileOperation:
    """Create a pending, dry-run-only proposal. Nothing touches disk yet."""
    op = ApprovedFileOperation(
        finding_id=finding_id,
        operation_type=operation_type,
        source_path=source_path,
        destination_path=destination_path,
        status=FileOperationStatus.PENDING_APPROVAL,
        dry_run=True,
        requested_by=requested_by,
    )
    session.add(op)
    session.flush()
    log_event(
        session,
        event_type="file_operation.proposed",
        summary=f"Proposed {operation_type.value} on '{source_path}' (dry run).",
        user_id=requested_by,
        entity_type="ApprovedFileOperation",
        entity_id=op.id,
    )
    return op


def approve_operation(
    session: Session, operation: ApprovedFileOperation, *, approved_by: uuid.UUID
) -> ApprovedFileOperation:
    operation.status = FileOperationStatus.APPROVED
    operation.approved_by = approved_by
    operation.approved_at = datetime.now(UTC)
    session.flush()
    log_event(
        session,
        event_type="file_operation.approved",
        summary=f"Approved {operation.operation_type.value} on '{operation.source_path}'.",
        user_id=approved_by,
        entity_type="ApprovedFileOperation",
        entity_id=operation.id,
    )
    return operation


def execute_operation(
    session: Session,
    operation: ApprovedFileOperation,
    *,
    allowed_roots: list[str],
    executed_by: uuid.UUID | None = None,
) -> ApprovedFileOperation:
    """Perform the approved, non-dry-run operation on disk.

    Requires ``status == APPROVED``. Refuses to overwrite an existing
    destination file and refuses any path outside the configured scanner
    roots, even if it was somehow approved.
    """
    if operation.status != FileOperationStatus.APPROVED:
        raise ValueError("Only an approved operation may be executed.")

    try:
        source = resolve_within_allowed_roots(operation.source_path, allowed_roots)
        destination = (
            resolve_within_allowed_roots(operation.destination_path, allowed_roots)
            if operation.destination_path
            else None
        )
    except PathSecurityError as exc:
        operation.status = FileOperationStatus.FAILED
        operation.result_detail = str(exc)
        session.flush()
        raise

    needs_destination = operation.operation_type in (
        FileOperationType.MOVE,
        FileOperationType.RENAME,
        FileOperationType.COPY,
    )
    if needs_destination and destination is None:
        operation.status = FileOperationStatus.FAILED
        operation.result_detail = "Operation requires a destination path but none was set."
        session.flush()
        raise ValueError(operation.result_detail)

    try:
        if operation.operation_type == FileOperationType.DELETE:
            source.unlink()
        elif operation.operation_type == FileOperationType.MOVE:
            dest = _require_destination(destination)
            _refuse_overwrite(dest)
            shutil.move(str(source), str(dest))
        elif operation.operation_type == FileOperationType.RENAME:
            dest = _require_destination(destination)
            _refuse_overwrite(dest)
            source.rename(dest)
        elif operation.operation_type == FileOperationType.COPY:
            dest = _require_destination(destination)
            _refuse_overwrite(dest)
            shutil.copy2(str(source), str(dest))
        elif operation.operation_type == FileOperationType.REPLACE:
            raise ValueError(
                "REPLACE is not permitted: ProducerOS never overwrites existing music files."
            )

        operation.status = FileOperationStatus.EXECUTED
        operation.executed_at = datetime.now(UTC)
        operation.result_detail = "Completed successfully."
    except Exception as exc:
        operation.status = FileOperationStatus.FAILED
        operation.result_detail = str(exc)
        session.flush()
        log_event(
            session,
            event_type="file_operation.failed",
            summary=f"Execution failed for {operation.operation_type.value} on '{operation.source_path}': {exc}",
            user_id=executed_by,
            entity_type="ApprovedFileOperation",
            entity_id=operation.id,
        )
        raise

    session.flush()
    log_event(
        session,
        event_type="file_operation.executed",
        summary=f"Executed {operation.operation_type.value} on '{operation.source_path}'.",
        user_id=executed_by,
        entity_type="ApprovedFileOperation",
        entity_id=operation.id,
    )
    return operation


def _require_destination(destination: Path | None) -> Path:
    """Runtime (not assert-based, so it survives ``python -O``) guarantee
    that a destination-taking operation actually has one."""
    if destination is None:
        raise ValueError("Operation requires a destination path but none was set.")
    return destination


def _refuse_overwrite(destination: Path) -> None:
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {destination}")
