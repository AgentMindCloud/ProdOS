"""Scanner dry-run and finding-approval integration tests (spec section 9)."""

from sqlalchemy import select

from produceros.demo.audio_fixtures import generate_sine_wav
from produceros.models.assets import AssetVersion
from produceros.models.enums import AssetType, FindingStatus, FindingType
from produceros.models.scanner import ScannerFinding
from produceros.services import catalog as catalog_service
from produceros.services import scanner as scanner_service
from produceros.services.assets import approve_finding_as_asset


def test_scan_is_read_only_and_finds_new_files(db_session, tmp_path):
    root_dir = tmp_path / "Music" / "Exports"
    root_dir.mkdir(parents=True)
    wav_path = generate_sine_wav(root_dir / "Producer_NewSong_MIX_v01.wav", seconds=0.5)

    scanner_service.add_root(db_session, path=str(root_dir))
    db_session.commit()

    run = scanner_service.trigger_scan(db_session)
    assert run.files_scanned == 1
    assert wav_path.exists()  # scanner never deletes/modifies the file

    findings = scanner_service.list_findings(db_session, run_id=run.id)
    assert len(findings) == 1
    assert findings[0].finding_type == FindingType.NEW_MIX_VERSION


def test_approving_a_finding_registers_an_asset_version(db_session, tmp_path):
    root_dir = tmp_path / "Music"
    root_dir.mkdir()
    generate_sine_wav(root_dir / "Producer_NewSong_MASTER_v01.wav", seconds=0.5)

    scanner_service.add_root(db_session, path=str(root_dir))
    run = scanner_service.trigger_scan(db_session)
    finding = scanner_service.list_findings(db_session, run_id=run.id)[0]
    assert finding.finding_type == FindingType.NEW_MASTER_VERSION

    project = catalog_service.create_project(db_session, working_title="New Song")
    version = approve_finding_as_asset(db_session, finding, project=project, asset_type=AssetType.MASTER)

    assert version.is_current
    db_session.refresh(finding)
    assert finding.status == FindingStatus.APPROVED
    assert finding.related_asset_version_id == version.id


def test_second_scan_does_not_re_report_registered_file(db_session, tmp_path):
    root_dir = tmp_path / "Music"
    root_dir.mkdir()
    generate_sine_wav(root_dir / "Producer_NewSong_MIX_v01.wav", seconds=0.5)

    scanner_service.add_root(db_session, path=str(root_dir))
    run1 = scanner_service.trigger_scan(db_session)
    finding = scanner_service.list_findings(db_session, run_id=run1.id)[0]

    project = catalog_service.create_project(db_session, working_title="New Song")
    approve_finding_as_asset(db_session, finding, project=project, asset_type=AssetType.MIX)

    run2 = scanner_service.trigger_scan(db_session)
    findings2 = scanner_service.list_findings(db_session, run_id=run2.id)
    assert findings2 == []  # already registered and unchanged -> no new finding


def test_scanner_rejects_paths_outside_configured_roots(db_session, tmp_path):
    allowed_root = tmp_path / "Allowed"
    allowed_root.mkdir()
    outside_dir = tmp_path / "Outside"
    outside_dir.mkdir()
    generate_sine_wav(outside_dir / "leaked.wav", seconds=0.2)

    scanner_service.add_root(db_session, path=str(allowed_root))
    run = scanner_service.trigger_scan(db_session)
    assert run.files_scanned == 0  # nothing under the outside dir was ever walked


def test_scan_detects_exact_duplicates(db_session, tmp_path):
    root_dir = tmp_path / "Music"
    root_dir.mkdir()
    content = generate_sine_wav(root_dir / "Producer_Song_MIX_v01.wav", seconds=0.5)

    scanner_service.add_root(db_session, path=str(root_dir))
    run1 = scanner_service.trigger_scan(db_session)
    finding = scanner_service.list_findings(db_session, run_id=run1.id)[0]
    project = catalog_service.create_project(db_session, working_title="Song")
    approve_finding_as_asset(db_session, finding, project=project, asset_type=AssetType.MIX)

    import shutil

    shutil.copy2(content, root_dir / "Producer_Song_MIX_v01_copy.wav")
    run2 = scanner_service.trigger_scan(db_session)
    findings2 = scanner_service.list_findings(db_session, run_id=run2.id)
    assert any(f.finding_type == FindingType.EXACT_DUPLICATE for f in findings2)
