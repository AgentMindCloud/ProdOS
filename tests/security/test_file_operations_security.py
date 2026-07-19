"""Unauthorized/unsafe file operations must never touch disk.

ProducerOS never deletes, renames, moves, or overwrites a file outside an
approved, re-validated operation. These tests exercise the service layer
directly since it is the last line of defense even if a caller misbehaves.
"""

from __future__ import annotations

import pytest

from produceros.models.enums import FileOperationStatus, FileOperationType
from produceros.security import PathSecurityError
from produceros.services import file_operations


def test_execute_refuses_a_non_approved_operation(db_session, tmp_path):
    root = tmp_path / "Music"
    root.mkdir()
    source = root / "track.wav"
    source.write_text("audio")

    op = file_operations.propose_operation(
        db_session, operation_type=FileOperationType.DELETE, source_path=str(source)
    )
    db_session.flush()

    with pytest.raises(ValueError):
        file_operations.execute_operation(db_session, op, allowed_roots=[str(root)])

    assert source.exists()


def test_execute_refuses_a_path_outside_allowed_roots_even_if_approved(db_session, tmp_path):
    root = tmp_path / "Music"
    root.mkdir()
    outside = tmp_path / "secret.wav"
    outside.write_text("private")

    op = file_operations.propose_operation(
        db_session, operation_type=FileOperationType.DELETE, source_path=str(outside)
    )
    op.status = FileOperationStatus.APPROVED
    db_session.flush()

    with pytest.raises(PathSecurityError):
        file_operations.execute_operation(db_session, op, allowed_roots=[str(root)])

    assert outside.exists()
    assert op.status == FileOperationStatus.FAILED


def test_execute_refuses_to_overwrite_existing_destination(db_session, tmp_path):
    root = tmp_path / "Music"
    root.mkdir()
    source = root / "a.wav"
    source.write_text("a")
    destination = root / "b.wav"
    destination.write_text("existing content")

    op = file_operations.propose_operation(
        db_session,
        operation_type=FileOperationType.MOVE,
        source_path=str(source),
        destination_path=str(destination),
    )
    op.status = FileOperationStatus.APPROVED
    db_session.flush()

    with pytest.raises(FileExistsError):
        file_operations.execute_operation(db_session, op, allowed_roots=[str(root)])

    assert destination.read_text() == "existing content"
    assert source.exists()


def test_replace_operation_type_is_never_permitted(db_session, tmp_path):
    root = tmp_path / "Music"
    root.mkdir()
    source = root / "a.wav"
    source.write_text("a")

    op = file_operations.propose_operation(
        db_session, operation_type=FileOperationType.REPLACE, source_path=str(source)
    )
    op.status = FileOperationStatus.APPROVED
    db_session.flush()

    with pytest.raises(ValueError, match="never overwrites"):
        file_operations.execute_operation(db_session, op, allowed_roots=[str(root)])


def test_execute_rejects_a_traversal_attempt_in_source_path(db_session, tmp_path):
    root = tmp_path / "Music"
    root.mkdir()
    outside = tmp_path / "secret.wav"
    outside.write_text("private")

    op = file_operations.propose_operation(
        db_session,
        operation_type=FileOperationType.DELETE,
        source_path=str(root / ".." / "secret.wav"),
    )
    op.status = FileOperationStatus.APPROVED
    db_session.flush()

    with pytest.raises(PathSecurityError):
        file_operations.execute_operation(db_session, op, allowed_roots=[str(root)])

    assert outside.exists()
