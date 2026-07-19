import json

from sqlalchemy import select

from produceros.delivery.manifest import check_completeness
from produceros.delivery.packaging import approve_package, create_package, execute_package, generate_manifest
from produceros.delivery.presets import seed_default_presets
from produceros.demo.audio_fixtures import generate_sine_wav
from produceros.models.delivery import DeliveryPreset
from produceros.models.enums import AssetType
from produceros.services import assets as asset_service
from produceros.services import catalog as catalog_service


def test_incomplete_package_reports_missing_assets(db_session):
    seed_default_presets(db_session)
    project = catalog_service.create_project(db_session, working_title="Delivery Track")
    preset = db_session.scalar(select(DeliveryPreset).where(DeliveryPreset.preset_type == "distributor"))

    completeness = check_completeness(db_session, project.id, preset)
    assert all(not c.present for c in completeness)


def test_generate_manifest_dry_run_does_not_touch_disk(db_session, tmp_path):
    seed_default_presets(db_session)
    project = catalog_service.create_project(db_session, working_title="Delivery Track")
    master_path = generate_sine_wav(tmp_path / "master.wav", seconds=0.3)
    asset_service.register_asset_version(db_session, project=project, asset_type=AssetType.MASTER, file_path=str(master_path), mark_current=True)
    artwork_path = tmp_path / "cover.jpg"
    artwork_path.write_bytes(b"\xff\xd8\xff" + b"\x00" * 20)
    asset_service.register_asset_version(db_session, project=project, asset_type=AssetType.ARTWORK, file_path=str(artwork_path), mark_current=True)

    preset = db_session.scalar(select(DeliveryPreset).where(DeliveryPreset.preset_type == "distributor"))
    output_dir = tmp_path / "delivery_out"
    package = create_package(db_session, project=project, preset=preset, name="Test Package", output_directory=str(output_dir))
    generate_manifest(db_session, package)

    assert package.status.value == "dry_run"
    assert not output_dir.exists()  # dry run: nothing copied yet
    assert len(package.items) == 2


def test_execute_package_copies_files_with_checksums_and_manifest(db_session, tmp_path):
    seed_default_presets(db_session)
    project = catalog_service.create_project(db_session, working_title="Delivery Track")
    master_path = generate_sine_wav(tmp_path / "master.wav", seconds=0.3)
    asset_service.register_asset_version(db_session, project=project, asset_type=AssetType.MASTER, file_path=str(master_path), mark_current=True)
    artwork_path = tmp_path / "cover.jpg"
    artwork_path.write_bytes(b"\xff\xd8\xff" + b"\x00" * 20)
    asset_service.register_asset_version(db_session, project=project, asset_type=AssetType.ARTWORK, file_path=str(artwork_path), mark_current=True)

    preset = db_session.scalar(select(DeliveryPreset).where(DeliveryPreset.preset_type == "distributor"))
    output_dir = tmp_path / "delivery_out"
    package = create_package(db_session, project=project, preset=preset, name="Test Package", output_directory=str(output_dir))
    generate_manifest(db_session, package)
    approve_package(db_session, package, approved_by=None)
    execute_package(db_session, package, executed_by=None)

    assert package.status.value == "completed"
    manifest_file = output_dir / "manifest.json"
    assert manifest_file.exists()
    manifest_data = json.loads(manifest_file.read_text())
    assert len(manifest_data["items"]) == 2
    for item in manifest_data["items"]:
        assert len(item["sha256"]) == 64


def test_execute_package_refuses_to_overwrite_existing_directory(db_session, tmp_path):
    seed_default_presets(db_session)
    project = catalog_service.create_project(db_session, working_title="Delivery Track")
    master_path = generate_sine_wav(tmp_path / "master.wav", seconds=0.3)
    asset_service.register_asset_version(db_session, project=project, asset_type=AssetType.MASTER, file_path=str(master_path), mark_current=True)

    preset = db_session.scalar(select(DeliveryPreset).where(DeliveryPreset.preset_type == "distributor"))
    output_dir = tmp_path / "delivery_out"
    output_dir.mkdir()
    (output_dir / "existing_file.txt").write_text("already here")

    package = create_package(db_session, project=project, preset=preset, name="Test Package", output_directory=str(output_dir))
    generate_manifest(db_session, package)
    approve_package(db_session, package, approved_by=None)

    import pytest

    with pytest.raises(FileExistsError):
        execute_package(db_session, package, executed_by=None)


def test_cannot_execute_package_without_approval(db_session, tmp_path):
    seed_default_presets(db_session)
    project = catalog_service.create_project(db_session, working_title="Delivery Track")
    preset = db_session.scalar(select(DeliveryPreset).where(DeliveryPreset.preset_type == "distributor"))
    package = create_package(db_session, project=project, preset=preset, name="Test Package", output_directory=str(tmp_path / "out"))
    generate_manifest(db_session, package)

    import pytest

    with pytest.raises(ValueError):
        execute_package(db_session, package, executed_by=None)
