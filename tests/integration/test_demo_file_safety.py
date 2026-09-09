"""Demo generation and cleanup must not overwrite or delete disk content."""

import os
import subprocess
from datetime import date
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import func, select

from produceros.demo import generator
from produceros.demo.audio_fixtures import generate_sine_wav
from produceros.demo.generator import DEMO_MANIFEST_KEY, clean_demo_data, load_demo_data
from produceros.models.analytics import AnalyticsImport, AnalyticsMetric, AnalyticsSource
from produceros.models.assets import AssetVersion
from produceros.models.catalog import Project
from produceros.models.delivery import DeliveryPackage
from produceros.models.enums import AnalyticsMetricType, AnalyticsSourceType
from produceros.models.scanner import ScannerFinding, ScannerRun
from produceros.services.analytics import add_manual_metric, get_or_create_source
from produceros.services.scanner import add_root
from produceros.services.settings import get_setting


def _snapshot_files(folder: Path) -> dict[Path, bytes]:
    return {
        path.relative_to(folder): path.read_bytes() for path in folder.rglob("*") if path.is_file()
    }


def _directory_alias(alias: Path, target: Path) -> None:
    """Use a real Windows junction or POSIX symlink, entirely in test storage."""
    if os.name == "nt":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(alias), str(target)],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=False,
        )
        if result.returncode != 0:
            pytest.skip("This test environment cannot create directory junctions.")
    else:
        alias.symlink_to(target, target_is_directory=True)


def test_audio_fixture_refuses_to_overwrite_an_existing_file(tmp_path):
    path = tmp_path / "My final master.wav"
    original = b"sentinel: user's existing audio must remain byte-for-byte unchanged"
    path.write_bytes(original)

    with pytest.raises(FileExistsError):
        generate_sine_wav(path, seconds=0.1)

    assert path.read_bytes() == original


def test_audio_fixture_rejects_a_hard_link_without_modifying_the_original(tmp_path):
    original = tmp_path / "My original.wav"
    original.write_bytes(b"original user audio")
    alias = tmp_path / "fixture.wav"
    alias.hardlink_to(original)

    with pytest.raises(ValueError, match="hard-linked"):
        generate_sine_wav(alias, seconds=0.1)

    assert original.read_bytes() == b"original user audio"
    assert alias.read_bytes() == b"original user audio"


def test_audio_fixture_rejects_linked_ancestors_before_creating_missing_parents(tmp_path):
    target = tmp_path / "personal audio"
    target.mkdir()
    sentinel = target / "Master.wav"
    sentinel.write_bytes(b"private original")
    alias = tmp_path / "redirected fixtures"
    _directory_alias(alias, target)

    with pytest.raises(ValueError, match="linked app storage path"):
        generate_sine_wav(alias / "not-created" / "nested" / "tone.wav", seconds=0.1)

    assert _snapshot_files(target) == {Path("Master.wav"): b"private original"}
    assert not (target / "not-created").exists()


def test_demo_load_rejects_a_linked_audio_directory_before_creating_files(
    db_session, data_dir, tmp_path
):
    target = tmp_path / "personal songs"
    target.mkdir()
    sentinel = target / "Track.wav"
    sentinel.write_bytes(b"personal song")
    _directory_alias(data_dir / "demo_audio", target)

    with pytest.raises(ValueError, match="linked app storage path"):
        load_demo_data(db_session)

    assert _snapshot_files(target) == {Path("Track.wav"): b"personal song"}
    assert list(target.iterdir()) == [sentinel]
    assert db_session.scalar(select(func.count()).select_from(Project)) == 0


def test_demo_cleanup_preserves_user_analytics_source_with_the_same_name(db_session):
    source = get_or_create_source(
        db_session, "Demo Streaming Report", AnalyticsSourceType.STREAMING
    )
    source.notes = "User-owned source; do not treat a matching name as demo ownership."
    metric = add_manual_metric(
        db_session,
        source=source,
        metric_type=AnalyticsMetricType.STREAMS,
        value=37,
        reporting_period_start=date(2026, 1, 1),
        reporting_period_end=date(2026, 1, 31),
    )
    source_id, metric_id, import_id = source.id, metric.id, metric.import_id
    db_session.commit()

    load_demo_data(db_session)
    db_session.commit()
    assert db_session.scalar(select(func.count()).select_from(AnalyticsSource)) == 2
    user_import_count = db_session.scalar(
        select(func.count())
        .select_from(AnalyticsImport)
        .where(AnalyticsImport.source_id == source_id)
    )
    assert user_import_count == 1  # demo values were not added to the user's source
    clean_demo_data(db_session)
    db_session.commit()
    db_session.expire_all()

    preserved = db_session.get(AnalyticsSource, source_id)
    assert preserved is not None
    assert preserved.notes == "User-owned source; do not treat a matching name as demo ownership."
    assert db_session.get(AnalyticsImport, import_id) is not None
    retained_metric = db_session.get(AnalyticsMetric, metric_id)
    assert retained_metric is not None and retained_metric.value == 37
    assert db_session.scalar(select(func.count()).select_from(AnalyticsSource)) == 1


def test_demo_run_directory_collision_fails_before_creating_records(
    db_session, data_dir, monkeypatch
):
    fixed_id = UUID(int=0)
    run_dir = data_dir / "demo_audio" / f"run-{fixed_id.hex}"
    run_dir.mkdir(parents=True)
    sentinel = run_dir / "My master.wav"
    sentinel.write_bytes(b"existing content in a colliding run folder")
    monkeypatch.setattr(generator.uuid, "uuid4", lambda: fixed_id)

    with pytest.raises(FileExistsError):
        load_demo_data(db_session)

    assert sentinel.read_bytes() == b"existing content in a colliding run folder"
    assert list(run_dir.iterdir()) == [sentinel]
    assert db_session.scalar(select(func.count()).select_from(Project)) == 0
    assert get_setting(db_session, DEMO_MANIFEST_KEY) is None


def test_demo_load_preserves_existing_folders_and_scans_only_its_new_run(
    db_session, data_dir, tmp_path
):
    audio_dir = data_dir / "demo_audio"
    audio_dir.mkdir()
    existing_master = audio_dir / "PRJ-0001_master_v01.wav"
    existing_master.write_bytes(b"existing audio with the old fixed demo filename")
    existing_extra = audio_dir / "user-content" / "notes.txt"
    existing_extra.parent.mkdir()
    existing_extra.write_bytes(b"user's notes")
    original_files = _snapshot_files(audio_dir)

    unrelated = tmp_path / "Real music folder"
    unrelated.mkdir()
    unrelated_file = unrelated / "Producer_RealSong_MIX_v01.wav"
    unrelated_file.write_bytes(b"do not scan unrelated music when loading the demo")
    unrelated_root = add_root(db_session, path=str(unrelated))

    summary = load_demo_data(db_session)
    db_session.commit()

    assert summary["projects"] == 6
    runs = list(db_session.scalars(select(ScannerRun)))
    assert len(runs) == 1
    run = runs[0]
    assert len(run.scanned_roots) == 1
    run_dir = Path(run.scanned_roots[0])
    assert run_dir.parent == audio_dir
    assert run_dir.name.startswith("run-")
    assert run.files_scanned == 6
    assert str(unrelated) not in run.scanned_roots
    assert unrelated_root.is_active
    assert all(
        Path(finding.path).is_relative_to(run_dir)
        for finding in db_session.scalars(select(ScannerFinding))
    )
    assert all(
        Path(version.full_path).parent == run_dir
        for version in db_session.scalars(select(AssetVersion))
    )
    assert {path: (audio_dir / path).read_bytes() for path in original_files} == original_files
    assert unrelated_file.read_bytes() == b"do not scan unrelated music when loading the demo"
    package = db_session.scalar(select(DeliveryPackage))
    assert package is not None
    output = Path(package.output_directory)
    assert output.parent == data_dir / "demo_deliveries" / run_dir.name
    assert not output.exists()  # demo packaging remains a dry run


def test_demo_clean_removes_database_records_and_preserves_every_file(db_session, data_dir):
    load_demo_data(db_session)
    db_session.commit()
    version = db_session.scalar(select(AssetVersion))
    assert version is not None
    run_dir = Path(version.full_path).parent
    personal_audio = run_dir / "My own song.wav"
    personal_audio.write_bytes(b"personal audio added beside demo fixtures")
    deliveries = data_dir / "demo_deliveries" / "user-package"
    deliveries.mkdir(parents=True)
    (deliveries / "Mix.wav").write_bytes(b"personal delivery audio")
    (deliveries / "notes.txt").write_bytes(b"personal delivery notes")
    audio_before = _snapshot_files(data_dir / "demo_audio")
    deliveries_before = _snapshot_files(data_dir / "demo_deliveries")

    removed = clean_demo_data(db_session)
    db_session.commit()

    assert removed > 0
    assert db_session.scalar(select(func.count()).select_from(Project)) == 0
    assert get_setting(db_session, DEMO_MANIFEST_KEY) is None
    assert _snapshot_files(data_dir / "demo_audio") == audio_before
    assert _snapshot_files(data_dir / "demo_deliveries") == deliveries_before
    assert clean_demo_data(db_session) == 0
    assert _snapshot_files(data_dir / "demo_audio") == audio_before


def test_demo_reload_after_clean_uses_new_files_and_preserves_previous_run(db_session, data_dir):
    load_demo_data(db_session)
    db_session.commit()
    original_files = _snapshot_files(data_dir / "demo_audio")
    previous_directories = set((data_dir / "demo_audio").iterdir())
    clean_demo_data(db_session)
    db_session.commit()

    load_demo_data(db_session)
    db_session.commit()

    current_directories = set((data_dir / "demo_audio").iterdir())
    assert previous_directories < current_directories
    assert len(current_directories - previous_directories) == 1
    assert {
        path: (data_dir / "demo_audio" / path).read_bytes() for path in original_files
    } == original_files


def test_repeated_load_refuses_to_replace_an_active_demo_manifest(db_session, data_dir):
    load_demo_data(db_session)
    db_session.commit()
    original_files = _snapshot_files(data_dir / "demo_audio")
    manifest_before = get_setting(db_session, DEMO_MANIFEST_KEY)

    with pytest.raises(ValueError, match="Demo records are already loaded"):
        load_demo_data(db_session)

    assert get_setting(db_session, DEMO_MANIFEST_KEY) == manifest_before
    assert db_session.scalar(select(func.count()).select_from(Project)) == 6
    assert _snapshot_files(data_dir / "demo_audio") == original_files
