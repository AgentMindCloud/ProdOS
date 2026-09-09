"""Delivery package lifecycle: draft -> dry-run manifest -> approval ->
execution (copy with checksums). Never overwrites an existing package
directory, always dry-run first, always audited (spec section 15)."""

from __future__ import annotations

import json
import stat
import uuid
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath, PureWindowsPath

from sqlalchemy import select
from sqlalchemy.orm import Session

from produceros.delivery.manifest import current_version_for_type
from produceros.filesystem import copy_file_exclusive
from produceros.models.assets import AssetVersion
from produceros.models.catalog import Project
from produceros.models.delivery import DeliveryManifestItem, DeliveryPackage, DeliveryPreset
from produceros.models.enums import AssetType, DeliveryPackageStatus
from produceros.scanners.hashing import hash_file
from produceros.services.audit import log_event


def _validate_components(parts: tuple[str, ...]) -> None:
    """Reject path aliases that can collide or escape on Windows."""
    for part in parts:
        stem = part.split(".", 1)[0].upper()
        reserved = stem in {"CON", "PRN", "AUX", "NUL"} or (
            len(stem) == 4 and stem[:3] in {"COM", "LPT"} and stem[-1] in "123456789¹²³"
        )
        if (
            part in {"", ".", ".."}
            or part.endswith((" ", "."))
            or any(ord(char) < 32 or char in '<>:"|?*' for char in part)
            or reserved
        ):
            raise ValueError("Delivery paths contain an unsafe or ambiguous filename.")


def _absolute_local_path(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute() or PureWindowsPath(raw).drive.startswith("\\\\"):
        raise ValueError("Delivery paths must be absolute paths on a local drive.")
    _validate_components(path.parts[1:])
    return path


def _relative_destination(raw: str) -> Path:
    # Validate both grammars even on POSIX: a manifest may have been imported
    # from Windows. Never let a drive, rooted path, or ADS be treated as a name.
    windows = PureWindowsPath(raw)
    portable = PurePosixPath(raw.replace("\\", "/"))
    if windows.drive or windows.root or portable.is_absolute() or not portable.parts:
        raise ValueError("Every delivery destination must be a relative file path.")
    _validate_components(portable.parts)
    if portable.parts[0].casefold() == "manifest.json":
        raise ValueError("manifest.json is reserved for the delivery manifest.")
    return Path(*portable.parts)


def _assert_no_links(path: Path) -> None:
    """Reject symlinks, junctions and other Windows reparse points in a path."""
    for component in (path, *path.parents):
        try:
            info = component.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Delivery paths cannot pass through symlinks or junctions.")


def _directory_identity(path: Path) -> tuple[int, int]:
    _assert_no_links(path)
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError("A delivery parent path is not a directory.")
    return info.st_dev, info.st_ino


def _check_directories(identities: dict[Path, tuple[int, int]]) -> None:
    for path, identity in identities.items():
        if _directory_identity(path) != identity:
            raise ValueError("A delivery directory changed during export. Choose a new folder.")


def _create_directories(path: Path, identities: dict[Path, tuple[int, int]]) -> None:
    """Exclusively create each missing directory; never adopt a racing folder."""
    missing = []
    current = path
    while current not in identities:
        if current == current.parent:
            raise ValueError("The delivery drive is unavailable.")
        missing.append(current)
        current = current.parent
    for directory in reversed(missing):
        _check_directories(identities)
        directory.mkdir(exist_ok=False)
        identities[directory] = _directory_identity(directory)


def _prepare_export(
    session: Session, package: DeliveryPackage
) -> tuple[
    Path, Project, list[tuple[DeliveryManifestItem, Path, Path]], dict[Path, tuple[int, int]]
]:
    if not package.output_directory:
        raise ValueError("Delivery package has no output directory set.")
    output = _absolute_local_path(package.output_directory)
    _assert_no_links(output)
    if output.exists():
        raise FileExistsError("The output path already exists. Choose a new delivery folder.")
    project = session.get(Project, package.project_id)
    if project is None:
        raise ValueError("Delivery package references a project that no longer exists.")

    plan = []
    destinations: set[tuple[str, ...]] = set()
    items = session.scalars(
        select(DeliveryManifestItem).where(DeliveryManifestItem.package_id == package.id)
    )
    for item in items:
        relative = _relative_destination(item.destination_relative_path)
        key = tuple(part.casefold() for part in relative.parts)
        if any(
            key[: len(existing)] == existing or existing[: len(key)] == key
            for existing in destinations
        ):
            raise ValueError("Delivery manifest destinations conflict with each other.")
        destinations.add(key)
        version = (
            session.get(AssetVersion, item.asset_version_id) if item.asset_version_id else None
        )
        if (
            version is None
            or version.asset is None
            or version.asset.project_id != package.project_id
        ):
            raise ValueError("A delivery source no longer belongs to this project's assets.")
        source = _absolute_local_path(item.source_path)
        registered_source = _absolute_local_path(version.full_path)
        _assert_no_links(source)
        _assert_no_links(registered_source)
        if source != registered_source or not source.is_file():
            raise ValueError("A delivery source is missing or differs from its registered asset.")
        destination = output / relative
        if not destination.is_relative_to(output) or source == destination:
            raise ValueError("A delivery destination is outside its folder or equals its source.")
        _assert_no_links(destination)
        plan.append((item, source, destination))

    identities = {}
    for parent in reversed(output.parents):
        if parent.exists():
            identities[parent] = _directory_identity(parent)
    if not identities:
        raise ValueError("The delivery drive is unavailable.")
    return output, project, plan, identities


def create_package(
    session: Session,
    *,
    project: Project,
    preset: DeliveryPreset,
    name: str,
    output_directory: str,
    user_id: uuid.UUID | None = None,
) -> DeliveryPackage:
    package = DeliveryPackage(
        project_id=project.id,
        preset_id=preset.id,
        name=name.strip(),
        status=DeliveryPackageStatus.DRAFT,
        output_directory=output_directory,
    )
    session.add(package)
    session.flush()
    log_event(
        session,
        event_type="delivery.package_created",
        summary=f"Delivery package '{package.name}' created for '{project.working_title}' ({preset.name}).",
        user_id=user_id,
        entity_type="DeliveryPackage",
        entity_id=package.id,
    )
    return package


def generate_manifest(
    session: Session, package: DeliveryPackage, *, user_id: uuid.UUID | None = None
) -> DeliveryPackage:
    """Dry-run manifest generation: computes what *would* be copied. Does
    not touch disk except to read source files for size, only real I/O
    happens in ``execute_package``."""
    preset = session.get(DeliveryPreset, package.preset_id)
    project = session.get(Project, package.project_id)
    if preset is None or project is None:
        raise ValueError("Delivery package references a preset or project that no longer exists.")

    session.query(DeliveryManifestItem).filter(
        DeliveryManifestItem.package_id == package.id
    ).delete()

    for raw_type in preset.required_asset_types:
        asset_type = AssetType(raw_type)
        version = current_version_for_type(session, project.id, asset_type)
        if version is None:
            continue
        destination = f"{asset_type.value}/{Path(version.original_filename).name}"
        session.add(
            DeliveryManifestItem(
                package_id=package.id,
                asset_version_id=version.id,
                role_in_package=asset_type.value.replace("_", " ").title(),
                source_path=version.full_path,
                destination_relative_path=destination,
                copied=False,
            )
        )

    package.status = DeliveryPackageStatus.DRY_RUN
    package.approved_by = None
    package.approved_at = None
    package.completed_at = None
    package.manifest_generated_at = datetime.now(UTC)
    session.flush()
    session.expire(package, ["items"])
    log_event(
        session,
        event_type="delivery.manifest_generated",
        summary=f"Manifest generated (dry run) for package '{package.name}'.",
        user_id=user_id,
        entity_type="DeliveryPackage",
        entity_id=package.id,
    )
    return package


def approve_package(
    session: Session, package: DeliveryPackage, *, approved_by: uuid.UUID
) -> DeliveryPackage:
    if package.status != DeliveryPackageStatus.DRY_RUN:
        raise ValueError("Generate the manifest before approving a package.")
    package.status = DeliveryPackageStatus.APPROVED
    package.approved_by = approved_by
    package.approved_at = datetime.now(UTC)
    session.flush()
    log_event(
        session,
        event_type="delivery.package_approved",
        summary=f"Delivery package '{package.name}' approved for copying.",
        user_id=approved_by,
        entity_type="DeliveryPackage",
        entity_id=package.id,
    )
    return package


def execute_package(
    session: Session, package: DeliveryPackage, *, executed_by: uuid.UUID | None = None
) -> DeliveryPackage:
    """Copy an approved manifest into a new, exclusively created directory.

    Validate all paths before creating anything, and exclusively create every
    copied file and manifest. An existing empty folder is refused too. Failed
    exports are retained for human inspection: cleanup never deletes files.
    """
    if package.status != DeliveryPackageStatus.APPROVED:
        raise ValueError("Only an approved package may be executed.")

    manifest_records = []

    try:
        output_dir, project, plan, identities = _prepare_export(session, package)
        _create_directories(output_dir, identities)
        for item, source, destination in plan:
            _create_directories(destination.parent, identities)
            _check_directories(identities)
            _assert_no_links(source)
            _assert_no_links(destination)
            copy_file_exclusive(source, destination)
            _check_directories(identities)
            _assert_no_links(destination)
            checksum = hash_file(destination)
            item.checksum_sha256 = checksum
            item.copied = True
            manifest_records.append(
                {
                    "role": item.role_in_package,
                    "original_filename": source.name,
                    "destination": item.destination_relative_path,
                    "sha256": checksum,
                }
            )

        manifest_payload = {
            "package_name": package.name,
            "project": project.working_title,
            "internal_code": project.internal_code,
            "generated_at": datetime.now(UTC).isoformat(),
            "items": manifest_records,
            "revision_notes": project.revision_notes or "",
        }
        _check_directories(identities)
        with (output_dir / "manifest.json").open("x", encoding="utf-8") as manifest_file:
            json.dump(manifest_payload, manifest_file, indent=2)

        package.status = DeliveryPackageStatus.COMPLETED
        package.completed_at = datetime.now(UTC)
    except Exception as exc:
        package.status = DeliveryPackageStatus.FAILED
        session.flush()
        log_event(
            session,
            event_type="delivery.package_failed",
            summary=f"Delivery package '{package.name}' execution failed: {exc}",
            user_id=executed_by,
            entity_type="DeliveryPackage",
            entity_id=package.id,
        )
        if isinstance(exc, OSError) and not isinstance(exc, FileExistsError):
            raise ValueError(
                "Delivery export could not finish. Any partial new files were kept; "
                "review them and choose a new output folder before retrying."
            ) from exc
        raise

    session.flush()
    log_event(
        session,
        event_type="delivery.package_completed",
        summary=f"Delivery package '{package.name}' copied to '{output_dir}'.",
        user_id=executed_by,
        entity_type="DeliveryPackage",
        entity_id=package.id,
    )
    return package
