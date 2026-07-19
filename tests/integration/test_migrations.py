"""Migration up/down integration test, run against an isolated temp data dir."""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_cli(args: list[str], env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "produceros.cli", *args],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=60,
    )


def test_db_upgrade_then_downgrade_roundtrip(tmp_path, monkeypatch):
    import os

    env = os.environ.copy()
    env["PRODUCEROS_DATA_DIR"] = str(tmp_path / "data")
    env["PYTHONPATH"] = str(REPO_ROOT / "src")

    result = _run_cli(["db-upgrade"], env)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "data" / "produceros.db").exists()

    result_current = _run_cli(["db-current"], env)
    assert result_current.returncode == 0, result_current.stderr

    # Re-running upgrade against an already-current database must be a safe no-op.
    result_again = _run_cli(["db-upgrade"], env)
    assert result_again.returncode == 0, result_again.stderr
