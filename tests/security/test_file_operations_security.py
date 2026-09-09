"""Unauthorized/unsafe file operations must never touch disk.

ProducerOS never deletes or overwrites user files. Copies/moves/renames
require approval and revalidated paths. Test the service as the last line
of defense even if a caller misbehaves.
"""

from __future__ import annotations

import errno
import os
from pathlib import Path

import pytest

from produceros import filesystem
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
        db_session,
        operation_type=FileOperationType.COPY,
        source_path=str(outside),
        destination_path=str(root / "copy.wav"),
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
        operation_type=FileOperationType.COPY,
        source_path=str(root / ".." / "secret.wav"),
        destination_path=str(root / "copy.wav"),
    )
    op.status = FileOperationStatus.APPROVED
    db_session.flush()

    with pytest.raises(PathSecurityError):
        file_operations.execute_operation(db_session, op, allowed_roots=[str(root)])

    assert outside.exists()


def test_delete_is_forbidden_even_for_an_old_approved_row(db_session, tmp_path):
    source = tmp_path / "keep.wav"
    source.write_bytes(b"irreplaceable synthetic fixture")
    op = file_operations.propose_operation(
        db_session, operation_type=FileOperationType.DELETE, source_path=str(source)
    )
    op.status = FileOperationStatus.APPROVED
    db_session.flush()

    with pytest.raises(ValueError, match="never deletes"):
        file_operations.execute_operation(db_session, op, allowed_roots=[str(tmp_path)])

    assert source.read_bytes() == b"irreplaceable synthetic fixture"


@pytest.mark.parametrize(
    "operation_type", [FileOperationType.COPY, FileOperationType.MOVE, FileOperationType.RENAME]
)
def test_destination_created_after_preflight_is_never_overwritten(
    db_session, tmp_path, monkeypatch, operation_type
):
    source = tmp_path / "source.wav"
    source.write_bytes(b"original source")
    destination = tmp_path / "destination.wav"
    op = file_operations.propose_operation(
        db_session,
        operation_type=operation_type,
        source_path=str(source),
        destination_path=str(destination),
    )
    op.status = FileOperationStatus.APPROVED
    db_session.flush()
    original_preflight = file_operations._refuse_overwrite

    def create_competing_file(path):
        original_preflight(path)
        path.write_bytes(b"another program's new content")

    monkeypatch.setattr(file_operations, "_refuse_overwrite", create_competing_file)
    with pytest.raises(FileExistsError):
        file_operations.execute_operation(db_session, op, allowed_roots=[str(tmp_path)])

    assert source.read_bytes() == b"original source"
    assert destination.read_bytes() == b"another program's new content"


@pytest.mark.parametrize(
    "operation_type", [FileOperationType.COPY, FileOperationType.MOVE, FileOperationType.RENAME]
)
def test_approved_supported_operation_preserves_content(
    db_session, admin_user, tmp_path, operation_type
):
    source = tmp_path / "original.wav"
    source.write_bytes(b"synthetic file content\0\1")
    destination = tmp_path / "renamed.wav"
    op = file_operations.propose_operation(
        db_session,
        operation_type=operation_type,
        source_path=str(source),
        destination_path=str(destination),
    )
    assert op.dry_run
    assert op.status == FileOperationStatus.PENDING_APPROVAL
    assert not destination.exists()
    file_operations.approve_operation(db_session, op, approved_by=admin_user.id)
    assert source.exists()
    assert not destination.exists()

    file_operations.execute_operation(
        db_session, op, allowed_roots=[str(tmp_path)], executed_by=admin_user.id
    )

    assert destination.read_bytes() == b"synthetic file content\0\1"
    assert source.exists() == (operation_type == FileOperationType.COPY)
    assert op.status == FileOperationStatus.EXECUTED
    assert not op.dry_run
    with pytest.raises(ValueError, match="pending"):
        file_operations.approve_operation(db_session, op, approved_by=admin_user.id)


@pytest.mark.parametrize("operation_type", [FileOperationType.DELETE, FileOperationType.REPLACE])
def test_destructive_proposals_cannot_be_approved(db_session, admin_user, operation_type):
    op = file_operations.propose_operation(
        db_session, operation_type=operation_type, source_path="not-accessed.wav"
    )
    with pytest.raises(ValueError, match="not permitted"):
        file_operations.approve_operation(db_session, op, approved_by=admin_user.id)
    assert op.status == FileOperationStatus.PENDING_APPROVAL
    assert op.dry_run


@pytest.mark.parametrize(
    "operation_type", [FileOperationType.COPY, FileOperationType.MOVE, FileOperationType.RENAME]
)
def test_existing_dangling_destination_is_refused(db_session, tmp_path, operation_type):
    source = tmp_path / "source.wav"
    source.write_bytes(b"source must survive")
    missing_target = tmp_path / "missing.wav"
    destination = tmp_path / "link.wav"
    try:
        destination.symlink_to(missing_target)
    except OSError:
        pytest.skip("Creating symlinks requires unavailable OS permission.")
    op = file_operations.propose_operation(
        db_session,
        operation_type=operation_type,
        source_path=str(source),
        destination_path=str(destination),
    )
    op.status = FileOperationStatus.APPROVED
    with pytest.raises(FileExistsError):
        file_operations.execute_operation(db_session, op, allowed_roots=[str(tmp_path)])
    assert source.read_bytes() == b"source must survive"
    assert destination.is_symlink()
    assert not missing_target.exists()


@pytest.mark.parametrize("error_code", [errno.EXDEV, errno.EACCES])
def test_failed_native_move_never_falls_back_to_copy_delete(
    db_session, tmp_path, monkeypatch, error_code
):
    source = tmp_path / "source.wav"
    source.write_bytes(b"preserve source")
    destination = tmp_path / "destination.wav"
    op = file_operations.propose_operation(
        db_session,
        operation_type=FileOperationType.MOVE,
        source_path=str(source),
        destination_path=str(destination),
    )
    op.status = FileOperationStatus.APPROVED

    def refuse_native_move(*args):
        raise OSError(error_code, "Native move refused")

    if filesystem.sys.platform == "win32":
        monkeypatch.setattr(filesystem.os, "rename", refuse_native_move)
    elif filesystem.sys.platform.startswith("linux"):
        monkeypatch.setattr(filesystem, "_rename_linux_noreplace", refuse_native_move)
    else:
        pytest.skip("Native file moves intentionally unsupported here.")

    with pytest.raises(OSError) as exc_info:
        file_operations.execute_operation(db_session, op, allowed_roots=[str(tmp_path)])
    assert exc_info.value.errno == error_code
    assert source.read_bytes() == b"preserve source"
    assert not destination.exists()
    assert op.status == FileOperationStatus.FAILED


def test_unsupported_platform_refuses_move_without_touching_files(tmp_path, monkeypatch):
    source = tmp_path / "source.wav"
    source.write_bytes(b"preserve source")
    destination = tmp_path / "destination.wav"
    monkeypatch.setattr(filesystem.sys, "platform", "unsupported")
    with pytest.raises(OSError) as exc_info:
        filesystem.rename_file_noreplace(source, destination)
    assert exc_info.value.errno == errno.ENOTSUP
    assert source.read_bytes() == b"preserve source"
    assert not destination.exists()


def test_linux_without_renameat2_has_no_unsafe_fallback(tmp_path, monkeypatch):
    source = tmp_path / "source.wav"
    source.write_bytes(b"preserve source")
    destination = tmp_path / "destination.wav"
    monkeypatch.setattr(filesystem.ctypes, "CDLL", lambda *args, **kwargs: object())
    with pytest.raises(OSError) as exc_info:
        filesystem._rename_linux_noreplace(source, destination)
    assert exc_info.value.errno == errno.ENOTSUP
    assert source.read_bytes() == b"preserve source"
    assert not destination.exists()


def test_interrupted_copy_keeps_source_and_new_partial_file(db_session, tmp_path, monkeypatch):
    source = tmp_path / "source.wav"
    source.write_bytes(b"abcdefghijkl")
    destination = tmp_path / "partial.wav"
    op = file_operations.propose_operation(
        db_session,
        operation_type=FileOperationType.COPY,
        source_path=str(source),
        destination_path=str(destination),
    )
    op.status = FileOperationStatus.APPROVED
    original_open = Path.open

    class InterruptedReader:
        def __init__(self, file):
            self.file = file
            self.reads = 0

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.file.close()

        def fileno(self):
            return self.file.fileno()

        def read(self, size):
            self.reads += 1
            if self.reads > 1:
                raise OSError(errno.EIO, "Simulated interrupted read")
            return self.file.read(size)

    def interrupted_open(path, mode="r", *args, **kwargs):
        opened = original_open(path, mode, *args, **kwargs)
        return InterruptedReader(opened) if path == source and mode == "rb" else opened

    with monkeypatch.context() as patch:
        patch.setattr(filesystem, "COPY_CHUNK_BYTES", 4)
        patch.setattr(Path, "open", interrupted_open)
        with pytest.raises(OSError, match="interrupted"):
            file_operations.execute_operation(db_session, op, allowed_roots=[str(tmp_path)])

    assert source.read_bytes() == b"abcdefghijkl"
    assert destination.read_bytes() == b"abcd"
    assert op.status == FileOperationStatus.FAILED
    assert not op.dry_run


@pytest.mark.skipif(os.name != "nt", reason="Windows path syntax only")
@pytest.mark.parametrize("name", ["other.wav:hidden", "NUL.wav", "other.wav.", "other.wav "])
def test_windows_ambiguous_destination_is_refused(db_session, tmp_path, name):
    source = tmp_path / "source.wav"
    source.write_bytes(b"preserve source")
    op = file_operations.propose_operation(
        db_session,
        operation_type=FileOperationType.COPY,
        source_path=str(source),
        destination_path=str(tmp_path / name),
    )
    op.status = FileOperationStatus.APPROVED
    with pytest.raises(PathSecurityError):
        file_operations.execute_operation(db_session, op, allowed_roots=[str(tmp_path)])
    assert source.read_bytes() == b"preserve source"
