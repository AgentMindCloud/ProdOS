"""The scanner must degrade gracefully -- never crash -- when it encounters
a file it cannot read (permission-denied, disappeared mid-scan, etc.)."""

from __future__ import annotations

import os
import stat

import pytest
from sqlalchemy import select

from produceros.models.enums import FindingType
from produceros.models.scanner import ScannerFinding, ScannerRoot
from produceros.scanners.engine import run_scan


def _findings(db_session, run):
    return list(db_session.scalars(select(ScannerFinding).where(ScannerFinding.run_id == run.id)))


def test_scanner_records_a_finding_for_an_unreadable_file_instead_of_crashing(db_session, tmp_path):
    root_dir = tmp_path / "Music"
    root_dir.mkdir()
    unreadable = root_dir / "locked.wav"
    unreadable.write_bytes(b"data")
    unreadable.chmod(0o000)

    try:
        if os.access(unreadable, os.R_OK):
            pytest.skip(
                "Running as a user that bypasses file permissions (e.g. root); cannot simulate."
            )

        root = ScannerRoot(path=str(root_dir), label="Music", is_active=True)
        db_session.add(root)
        db_session.flush()

        run = run_scan(db_session, roots=[root], allowed_extensions=[".wav"])

        assert run.status.value == "completed"
        assert any(f.finding_type == FindingType.LOCKED_FILE for f in _findings(db_session, run))
    finally:
        unreadable.chmod(stat.S_IWUSR | stat.S_IRUSR)


def test_scanner_records_finding_for_missing_root_instead_of_crashing(db_session, tmp_path):
    missing_root = tmp_path / "DoesNotExist"
    root = ScannerRoot(path=str(missing_root), label="Missing", is_active=True)
    db_session.add(root)
    db_session.flush()

    run = run_scan(db_session, roots=[root], allowed_extensions=[".wav"])

    assert run.status.value == "completed"
    assert any(f.finding_type == FindingType.INVALID_PATH for f in _findings(db_session, run))
