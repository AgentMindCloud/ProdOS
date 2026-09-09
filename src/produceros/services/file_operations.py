"""Approved, audited file operations (spec sections 2 and 9).

ProducerOS never deletes or overwrites user files, even with approval.
Copies and same-filesystem moves/renames require an explicit approval and
are logged before and after execution. Proposals remain dry-run records.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from pathlib import Path, PureWindowsPath

from sqlalchemy.orm import Session

from produceros.filesystem import copy_file_exclusive, rename_file_noreplace
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
    _refuse_forbidden_type(operation.operation_type)
    if operation.status != FileOperationStatus.PENDING_APPROVAL:
        raise ValueError("Only a pending dry-run proposal may be approved.")
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

    Requires ``status == APPROVED``. DELETE and REPLACE are permanently
    forbidden, including historical approvals. Every supported operation
    refuses existing destinations at the native filesystem operation.
    """
    if operation.status != FileOperationStatus.APPROVED:
        raise ValueError("Only an approved operation may be executed.")

    try:
        _refuse_forbidden_type(operation.operation_type)
        if operation.operation_type not in (
            FileOperationType.MOVE,
            FileOperationType.RENAME,
            FileOperationType.COPY,
        ):
            raise ValueError("Unsupported file operation.")

        source_path = Path(operation.source_path)
        _validate_file_path(source_path)
        if source_path.is_symlink():
            raise PathSecurityError("Source links are not supported; select the ordinary file.")
        source = resolve_within_allowed_roots(source_path, allowed_roots)
        if not operation.destination_path:
            raise ValueError("Operation requires a destination path but none was set.")

        destination_path = Path(operation.destination_path)
        _validate_file_path(destination_path)
        # Validate the full path, but resolve only its parent for execution:
        # resolving the final component could follow a dangling destination
        # link and create its target instead of refusing the existing link.
        resolve_within_allowed_roots(destination_path, allowed_roots)
        destination = (
            resolve_within_allowed_roots(destination_path.parent, allowed_roots)
            / destination_path.name
        )
        _refuse_overwrite(destination)

        operation.dry_run = False
        if operation.operation_type == FileOperationType.COPY:
            copy_file_exclusive(source, destination)
        else:
            rename_file_noreplace(source, destination)

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


def _refuse_overwrite(destination: Path) -> None:
    if os.path.lexists(destination):
        raise FileExistsError(f"Refusing to overwrite existing file: {destination}")


def _refuse_forbidden_type(operation_type: FileOperationType) -> None:
    if operation_type == FileOperationType.DELETE:
        raise ValueError("DELETE is not permitted: ProducerOS never deletes user files.")
    if operation_type == FileOperationType.REPLACE:
        raise ValueError(
            "REPLACE is not permitted: ProducerOS never overwrites existing music files."
        )


def _validate_file_path(path: Path) -> None:
    if os.name == "nt" and any(
        ":" in part or part.endswith((".", " ")) or PureWindowsPath(part).is_reserved()
        for part in path.parts
        if part != path.anchor
    ):
        raise PathSecurityError(
            "Windows device names, alternate streams, and ambiguous paths are refused."
        )
