"""CLI-level coverage for the restore-dry-run / restore subcommands added
for scripts/restore.ps1 -- argument wiring and the --yes confirmation
gate, not the underlying restore mechanics (covered in
tests/integration/test_backup_and_restore.py)."""

from __future__ import annotations

import pytest

from produceros.cli import build_parser, main


def test_restore_dry_run_reports_a_missing_file(capsys):
    with pytest.raises(SystemExit):
        main(["restore-dry-run", "/does/not/exist.db"])
    captured = capsys.readouterr()
    assert "OK: False" in captured.out


def test_restore_without_yes_is_refused(capsys, tmp_path):
    fake_backup = tmp_path / "backup.db"
    fake_backup.write_bytes(b"not a real sqlite file")

    with pytest.raises(SystemExit):
        main(["restore", str(fake_backup)])

    captured = capsys.readouterr()
    assert "--yes" in captured.out


def test_restore_dry_run_parses_positional_backup_path():
    parser = build_parser()
    args = parser.parse_args(["restore-dry-run", "/tmp/some-backup.db"])
    assert args.backup_path == "/tmp/some-backup.db"
    assert args.func.__name__ == "cmd_restore_dry_run"


def test_restore_parses_yes_flag():
    parser = build_parser()
    args = parser.parse_args(["restore", "/tmp/some-backup.db", "--yes"])
    assert args.backup_path == "/tmp/some-backup.db"
    assert args.yes is True
    assert args.func.__name__ == "cmd_restore"
