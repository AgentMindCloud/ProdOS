"""Delivery package lifecycle: draft -> dry-run manifest -> approval ->
execution (copy with checksums). Never overwrites an existing package
directory, always dry-run first, always audited (spec section 15)."""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from produceros.delivery.manifest import current_version_for_type
from produceros.models.catalog import Project
from produceros.models.delivery import DeliveryManifestItem, DeliveryPackage, DeliveryPreset
from produceros.models.enums import AssetType, DeliveryPackageStatus
from produceros.scanners.hashing import hash_file
from produceros.services.audit import log_event


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
    package.manifest_generated_at = datetime.now(UTC)
    session.flush()
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
    """Copy every manifest item into the output directory, computing a
    checksum for each. Refuses to run if the output directory already
    exists and is non-empty (never overwrite an existing package)."""
    if package.status != DeliveryPackageStatus.APPROVED:
        raise ValueError("Only an approved package may be executed.")

    if not package.output_directory:
        raise ValueError("Delivery package has no output directory set.")
    output_dir = Path(package.output_directory)
    if output_dir.exists() and any(output_dir.iterdir()):
        package.status = DeliveryPackageStatus.FAILED
        session.flush()
        raise FileExistsError(f"Output directory '{output_dir}' already exists and is not empty.")

    output_dir.mkdir(parents=True, exist_ok=True)

    project = session.get(Project, package.project_id)
    if project is None:
        raise ValueError("Delivery package references a project that no longer exists.")
    items = list(package.items)
    manifest_records = []

    try:
        for item in items:
            source = Path(item.source_path)
            destination = output_dir / item.destination_relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
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
        (output_dir / "manifest.json").write_text(
            json.dumps(manifest_payload, indent=2), encoding="utf-8"
        )

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
