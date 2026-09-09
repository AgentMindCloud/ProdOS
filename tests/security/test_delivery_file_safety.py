"""Delivery approval must never authorize overwriting or escaping its folder."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from produceros.delivery.packaging import (
    approve_package,
    create_package,
    execute_package,
    generate_manifest,
)
from produceros.delivery.presets import seed_default_presets
from produceros.models.delivery import DeliveryManifestItem, DeliveryPreset
from produceros.models.enums import AssetType
from produceros.services import assets as asset_service
from produceros.services import catalog as catalog_service


def _approved_package(db_session, tmp_path):
    seed_default_presets(db_session)
    project = catalog_service.create_project(db_session, working_title="Safety fixture")
    source = tmp_path / "source.wav"
    source.write_bytes(b"synthetic source sentinel")
    version = asset_service.register_asset_version(
        db_session,
        project=project,
        asset_type=AssetType.MASTER,
        file_path=str(source),
        mark_current=True,
    )
    preset = db_session.scalar(
        select(DeliveryPreset).where(DeliveryPreset.preset_type == "distributor")
    )
    output = tmp_path / "new-export"
    package = create_package(
        db_session,
        project=project,
        preset=preset,
        name="Safety fixture",
        output_directory=str(output),
    )
    generate_manifest(db_session, package)
    approve_package(db_session, package, approved_by=None)
    return package, version, source, output


@pytest.mark.parametrize("existing_kind", ["empty_directory", "populated_directory", "file"])
def test_export_never_uses_an_existing_output(db_session, tmp_path, existing_kind):
    package, _, source, output = _approved_package(db_session, tmp_path)
    if existing_kind == "file":
        output.write_bytes(b"output sentinel")
    else:
        output.mkdir()
        if existing_kind == "populated_directory":
            (output / "manifest.json").write_bytes(b"manifest sentinel")

    with pytest.raises(FileExistsError):
        execute_package(db_session, package)

    assert source.read_bytes() == b"synthetic source sentinel"
    if existing_kind == "file":
        assert output.read_bytes() == b"output sentinel"
    elif existing_kind == "populated_directory":
        assert (output / "manifest.json").read_bytes() == b"manifest sentinel"
        assert list(output.iterdir()) == [output / "manifest.json"]
    else:
        assert list(output.iterdir()) == []


@pytest.mark.parametrize(
    "destination",
    [
        "../source.wav",
        "master/../../source.wav",
        "..\\source.wav",
        "/source.wav",
        "C:\\source.wav",
        "C:source.wav",
        "\\\\server\\share\\source.wav",
        "master/file.wav:stream",
        "master/file.wav.",
        "master/CON.wav",
        "manifest.json",
        "manifest.json/file.wav",
    ],
)
def test_all_manifest_destinations_are_validated_before_writes(db_session, tmp_path, destination):
    package, _, source, output = _approved_package(db_session, tmp_path)
    package.items[0].destination_relative_path = destination
    db_session.flush()

    with pytest.raises(ValueError):
        execute_package(db_session, package)

    assert not output.exists()
    assert source.read_bytes() == b"synthetic source sentinel"


def test_absolute_destination_cannot_overwrite_source(db_session, tmp_path):
    package, _, source, output = _approved_package(db_session, tmp_path)
    package.items[0].destination_relative_path = str(source)

    with pytest.raises(ValueError):
        execute_package(db_session, package)

    assert source.read_bytes() == b"synthetic source sentinel"
    assert not output.exists()


@pytest.mark.parametrize("destination", ["MASTER/SOURCE.WAV", "master/source.wav/child.wav"])
def test_manifest_collisions_fail_before_output_creation(db_session, tmp_path, destination):
    package, version, source, output = _approved_package(db_session, tmp_path)
    package.items.append(
        DeliveryManifestItem(
            asset_version_id=version.id,
            source_path=str(source),
            destination_relative_path=destination,
            role_in_package="Injected collision",
        )
    )
    db_session.flush()

    with pytest.raises(ValueError):
        execute_package(db_session, package)

    assert not output.exists()
    assert source.read_bytes() == b"synthetic source sentinel"


@pytest.mark.parametrize("bad_source", ["missing", "directory", "relative", "changed_pointer"])
def test_source_preflight_finishes_before_any_export_writes(db_session, tmp_path, bad_source):
    package, version, source, output = _approved_package(db_session, tmp_path)
    item = package.items[0]
    if bad_source == "missing":
        item.source_path = version.full_path = str(tmp_path / "missing.wav")
    elif bad_source == "directory":
        item.source_path = version.full_path = str(tmp_path)
    elif bad_source == "relative":
        item.source_path = version.full_path = "source.wav"
    else:
        other = tmp_path / "unapproved.wav"
        other.write_bytes(b"unapproved sentinel")
        item.source_path = str(other)

    with pytest.raises(ValueError):
        execute_package(db_session, package)

    assert not output.exists()
    assert source.read_bytes() == b"synthetic source sentinel"


def test_approved_manifest_cannot_reference_another_projects_asset(db_session, tmp_path):
    package, version, source, output = _approved_package(db_session, tmp_path)
    other_project = catalog_service.create_project(db_session, working_title="Other project")
    version.asset.project_id = other_project.id
    db_session.flush()

    with pytest.raises(ValueError):
        execute_package(db_session, package)

    assert not output.exists()
    assert source.read_bytes() == b"synthetic source sentinel"


def test_relative_output_is_rejected(db_session, tmp_path, monkeypatch):
    package, _, source, output = _approved_package(db_session, tmp_path)
    package.output_directory = "new-export"
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError):
        execute_package(db_session, package)

    assert not output.exists()
    assert source.read_bytes() == b"synthetic source sentinel"


def test_symlink_output_parent_is_rejected(db_session, tmp_path):
    package, _, source, _ = _approved_package(db_session, tmp_path)
    actual = tmp_path / "actual"
    actual.mkdir()
    sentinel = actual / "sentinel.wav"
    sentinel.write_bytes(b"outside sentinel")
    link = tmp_path / "link"
    try:
        link.symlink_to(actual, target_is_directory=True)
    except OSError:
        pytest.skip("This Windows account cannot create symlinks")
    package.output_directory = str(link / "new-export")

    with pytest.raises(ValueError):
        execute_package(db_session, package)

    assert list(actual.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b"outside sentinel"
    assert source.read_bytes() == b"synthetic source sentinel"


def test_copy_collision_preserves_preexisting_file_and_partial_export(
    db_session, tmp_path, monkeypatch
):
    from produceros.delivery import packaging

    package, _, source, output = _approved_package(db_session, tmp_path)
    original_copy = packaging.copy_file_exclusive

    def introduce_collision(source_path, destination_path):
        destination_path.write_bytes(b"concurrent sentinel")
        original_copy(source_path, destination_path)

    monkeypatch.setattr(packaging, "copy_file_exclusive", introduce_collision)

    with pytest.raises(FileExistsError):
        execute_package(db_session, package)

    assert (output / "master" / "source.wav").read_bytes() == b"concurrent sentinel"
    assert not (output / "manifest.json").exists()
    assert source.read_bytes() == b"synthetic source sentinel"


def test_manifest_collision_is_exclusive_and_never_cleaned_up(db_session, tmp_path, monkeypatch):
    from produceros.delivery import packaging

    package, _, source, output = _approved_package(db_session, tmp_path)
    original_copy = packaging.copy_file_exclusive

    def create_foreign_manifest(source_path, destination_path):
        original_copy(source_path, destination_path)
        (output / "manifest.json").write_bytes(b"concurrent manifest sentinel")

    monkeypatch.setattr(packaging, "copy_file_exclusive", create_foreign_manifest)

    with pytest.raises(FileExistsError):
        execute_package(db_session, package)

    assert (output / "manifest.json").read_bytes() == b"concurrent manifest sentinel"
    assert (output / "master" / "source.wav").read_bytes() == source.read_bytes()
