"""Asset / AssetVersion registration and "current version" management
(spec sections 8, 10, 11)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from produceros.audio.metadata import extract_metadata
from produceros.models.assets import Asset, AssetVersion, AudioAnalysis
from produceros.models.catalog import Project
from produceros.models.enums import (
    ApprovalStatus,
    AssetRegisteredVia,
    AssetType,
    MetadataConfidence,
)
from produceros.models.scanner import ScannerFinding
from produceros.scanners.filename_parser import parse_filename
from produceros.scanners.hashing import hash_file
from produceros.services.audit import log_event


def get_or_create_asset(
    session: Session,
    *,
    project_id: uuid.UUID,
    asset_type: AssetType,
    label: str | None = None,
    track_id: uuid.UUID | None = None,
) -> Asset:
    stmt = select(Asset).where(Asset.project_id == project_id, Asset.asset_type == asset_type)
    if track_id:
        stmt = stmt.where(Asset.track_id == track_id)
    asset = session.scalar(stmt)
    if asset is None:
        asset = Asset(
            project_id=project_id,
            track_id=track_id,
            asset_type=asset_type,
            label=label or asset_type.value.replace("_", " ").title(),
        )
        session.add(asset)
        session.flush()
    return asset


def register_asset_version(
    session: Session,
    *,
    project: Project,
    asset_type: AssetType,
    file_path: str,
    registered_via: AssetRegisteredVia = AssetRegisteredVia.MANUAL,
    approval_status: ApprovalStatus = ApprovalStatus.PENDING,
    mark_current: bool = False,
    user_id: uuid.UUID | None = None,
    track_id: uuid.UUID | None = None,
) -> AssetVersion:
    """Register a file as a new version of a project's Asset "slot".

    Historical versions are never deleted or overwritten; this always
    inserts a new AssetVersion row. Filename parsing and (when possible)
    audio metadata extraction happen automatically and are stored as
    ``embedded``/``measured`` data -- never as ``user_confirmed``.
    """
    path = Path(file_path)
    asset = get_or_create_asset(
        session, project_id=project.id, asset_type=asset_type, track_id=track_id
    )

    parsed = parse_filename(path.name)
    content_hash = hash_file(path) if path.exists() else None
    size_bytes = path.stat().st_size if path.exists() else None
    modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC) if path.exists() else None

    existing_versions = session.scalars(
        select(AssetVersion).where(AssetVersion.asset_id == asset.id)
    ).all()
    next_version_number = (max((v.version_number for v in existing_versions), default=0)) + 1

    version = AssetVersion(
        asset_id=asset.id,
        version_number=next_version_number,
        original_filename=path.name,
        full_path=str(path),
        content_hash=content_hash,
        size_bytes=size_bytes,
        modified_at=modified_at,
        parsed_artist=parsed.artist,
        parsed_track=parsed.track,
        parsed_mix_or_master=parsed.mix_or_master,
        parsed_version_label=parsed.version_label,
        parsed_date=parsed.parsed_date,
        parsed_bpm=parsed.bpm,
        parsed_key=parsed.musical_key,
        parsed_metadata=parsed.as_metadata_dict(),
        approval_status=approval_status,
        registered_via=registered_via,
        is_current=False,
    )
    session.add(version)
    session.flush()

    if path.exists() and asset_type not in (AssetType.OTHER,):
        _attach_audio_analysis(session, version, path)

    if mark_current:
        set_current_version(session, asset, version, user_id=user_id)

    log_event(
        session,
        event_type="asset.version_registered",
        summary=f"Registered '{path.name}' as {asset_type.value} v{next_version_number} for '{project.working_title}'.",
        user_id=user_id,
        entity_type="AssetVersion",
        entity_id=version.id,
    )
    return version


def _attach_audio_analysis(session: Session, version: AssetVersion, path: Path) -> None:
    extracted = extract_metadata(path)
    if not extracted.is_audio and not extracted.warnings:
        return
    analysis = AudioAnalysis(
        asset_version_id=version.id,
        file_type=extracted.file_type,
        duration_seconds=extracted.duration_seconds,
        sample_rate=extracted.sample_rate,
        bit_depth=extracted.bit_depth,
        channels=extracted.channels,
        file_size_bytes=extracted.file_size_bytes,
        embedded_title=extracted.embedded_title,
        embedded_artist=extracted.embedded_artist,
        embedded_album=extracted.embedded_album,
        embedded_track_number=extracted.embedded_track_number,
        bpm_source=MetadataConfidence.EMBEDDED if version.parsed_bpm else None,
        key_source=MetadataConfidence.EMBEDDED if version.parsed_key else None,
        analyzed_at=datetime.now(UTC),
        warnings=extracted.warnings,
    )
    session.add(analysis)
    session.flush()


def set_current_version(
    session: Session, asset: Asset, version: AssetVersion, *, user_id: uuid.UUID | None = None
) -> AssetVersion:
    """Mark ``version`` as the single current version for its Asset slot,
    demoting any previously current version of the same asset."""
    if version.asset_id != asset.id:
        raise ValueError("Version does not belong to this asset.")

    others = session.scalars(
        select(AssetVersion).where(
            AssetVersion.asset_id == asset.id, AssetVersion.is_current.is_(True)
        )
    )
    for other in others:
        other.is_current = False

    version.is_current = True
    version.approval_status = ApprovalStatus.APPROVED
    session.flush()
    log_event(
        session,
        event_type="asset.version_marked_current",
        summary=f"'{version.original_filename}' marked current for asset '{asset.label}'.",
        user_id=user_id,
        entity_type="AssetVersion",
        entity_id=version.id,
    )
    return version


def approve_finding_as_asset(
    session: Session,
    finding: ScannerFinding,
    *,
    project: Project,
    asset_type: AssetType,
    user_id: uuid.UUID | None = None,
    mark_current: bool = True,
) -> AssetVersion:
    """Turn an approved scanner finding into a registered AssetVersion."""
    from produceros.models.enums import FindingStatus

    version = register_asset_version(
        session,
        project=project,
        asset_type=asset_type,
        file_path=finding.path,
        registered_via=AssetRegisteredVia.SCANNER,
        approval_status=ApprovalStatus.APPROVED,
        mark_current=mark_current,
        user_id=user_id,
    )
    finding.status = FindingStatus.APPROVED
    finding.resolved_at = datetime.now(UTC)
    finding.resolved_by = user_id
    finding.related_asset_version_id = version.id
    session.flush()
    log_event(
        session,
        event_type="scanner.finding_approved",
        summary=f"Finding for '{finding.path}' approved and registered as asset version.",
        user_id=user_id,
        entity_type="ScannerFinding",
        entity_id=finding.id,
    )
    return version
