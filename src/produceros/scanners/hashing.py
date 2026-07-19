"""Content hashing for exact-duplicate detection (spec section 9)."""

from __future__ import annotations

import hashlib
from pathlib import Path

CHUNK_SIZE = 1024 * 1024


def hash_file(path: str | Path) -> str:
    """Return the sha256 hex digest of a file, streamed in 1 MiB chunks so
    multi-gigabyte masters/stems don't need to be loaded into memory."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()
