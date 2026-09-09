"""No-clobber file primitives for explicitly approved operations.

Callers still own approval and allowed-root validation. These functions
never delete files or fall back to an overwrite/copy-and-delete operation.
They do not sandbox a process against hostile concurrent parent-directory
changes by another program running as the same operating-system user.
"""

from __future__ import annotations

import ctypes
import errno
import os
import stat
import sys
from pathlib import Path

COPY_CHUNK_BYTES = 1024 * 1024


def _require_regular_file(path: Path) -> os.stat_result:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(
            "Only ordinary files may be copied or moved; links and folders are refused."
        )
    return info


def copy_file_exclusive(source: Path, destination: Path) -> None:
    """Stream source into a newly created destination, never an existing one.

    Exclusive creation rejects existing files, folders, and dangling links
    at the actual open operation, including arrivals after a caller's check.
    If copying fails, keep the partial new file for inspection; never delete
    it automatically or reopen a destination path to change its metadata.
    """
    expected = _require_regular_file(source)
    with source.open("rb") as input_file:
        opened = os.fstat(input_file.fileno())
        if not stat.S_ISREG(opened.st_mode) or not os.path.samestat(expected, opened):
            raise ValueError("Source file changed before copying; review the operation again.")
        with destination.open("xb") as output_file:
            while chunk := input_file.read(COPY_CHUNK_BYTES):
                output_file.write(chunk)


def _rename_linux_noreplace(source: Path, destination: Path) -> None:
    # Linux renameat2(RENAME_NOREPLACE) is the no-overwrite primitive.
    # A plain POSIX rename would silently replace a concurrent destination.
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise OSError(errno.ENOTSUP, "This system does not support no-replace file moves.")
    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    at_fdcwd = -100
    rename_noreplace = 1
    result = renameat2(
        at_fdcwd, os.fsencode(source), at_fdcwd, os.fsencode(destination), rename_noreplace
    )
    if result != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(destination))


def rename_file_noreplace(source: Path, destination: Path) -> None:
    """Move one ordinary file without replacing an existing destination.

    Windows os.rename refuses an existing destination. Linux uses
    renameat2(RENAME_NOREPLACE); unsupported platforms/filesystems and
    cross-device moves fail closed. No shutil.move or copy/delete fallback.
    """
    _require_regular_file(source)
    if sys.platform == "win32":
        os.rename(source, destination)
    elif sys.platform.startswith("linux"):
        _rename_linux_noreplace(source, destination)
    else:
        raise OSError(errno.ENOTSUP, "No-replace file moves are not supported on this platform.")
