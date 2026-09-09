"""Read-only, root-restricted access to already registered local media.

No file is copied, analyzed, converted, or loaded into memory here. The
HTTP route uses FileResponse to stream bytes only when a preview is requested.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from produceros.config import get_settings
from produceros.models.assets import Asset, AssetVersion
from produceros.models.catalog import Project
from produceros.models.enums import AssetType
from produceros.models.scanner import ScannerRoot
from produceros.security import PathSecurityError, resolve_within_allowed_roots

AUDIO_TYPES = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".m4a": "audio/mp4",
    ".aiff": "audio/aiff",
    ".aif": "audio/aiff",
}
ARTWORK_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


@dataclass(frozen=True)
class PreviewFile:
    path: Path
    media_type: str


class ProjectMedia(TypedDict):
    audio: AssetVersion | None
    artwork: AssetVersion | None


def preview_file(session: Session, version: AssetVersion) -> PreviewFile | None:
    """Return a safe local preview target, or None without exposing its path.

    Registration alone is not permission to serve arbitrary local files: the
    target must also be inside an active scanner root or its project's explicit
    root. The application data directory is always excluded, even beneath an
    overly broad configured root. Extension checks apply after resolving symlinks.
    """
    asset = session.get(Asset, version.asset_id)
    if asset is None:
        return None
    project = session.get(Project, asset.project_id)
    if project is None:
        return None

    settings = get_settings()
    roots = list(settings.scanner_roots)
    roots.extend(session.scalars(select(ScannerRoot.path).where(ScannerRoot.is_active.is_(True))))
    if project.project_root_path:
        roots.append(project.project_root_path)

    try:
        candidate = Path(version.full_path)
        # Never interpret a relative path against a developer's working folder,
        # or a Windows alternate data stream as an ordinary music file.
        if not candidate.is_absolute() or any(":" in part for part in candidate.parts[1:]):
            return None
        if candidate.suffix.lower() not in AUDIO_TYPES | ARTWORK_TYPES:
            return None
        roots = [root for root in roots if Path(root).is_absolute()]
        path = resolve_within_allowed_roots(candidate, roots)
        if path.is_relative_to(settings.data_dir.resolve()) or not path.is_file():
            return None
        suffix = path.suffix.lower()
        media_type = AUDIO_TYPES.get(suffix)
        if media_type is None and asset.asset_type == AssetType.ARTWORK:
            media_type = ARTWORK_TYPES.get(suffix)
        if media_type is None:
            return None
        return PreviewFile(path=path, media_type=media_type)
    except (OSError, ValueError, RuntimeError, PathSecurityError):
        return None


def project_media(session: Session, project: Project) -> ProjectMedia:
    """Choose current, available project media for a player and cover image.

    Project pointer fields are not database foreign keys, so ownership is checked
    before using them. Missing files and disallowed roots render as unavailable.
    Browser codec support is still required; no transcoding is attempted.
    """
    versions = list(
        session.scalars(
            select(AssetVersion)
            .join(Asset)
            .where(
                Asset.project_id == project.id,
                or_(
                    AssetVersion.is_current.is_(True),
                    AssetVersion.id.in_(
                        pointer
                        for pointer in (
                            project.current_master_asset_version_id,
                            project.current_mix_asset_version_id,
                            project.artwork_asset_version_id,
                        )
                        if pointer is not None
                    ),
                ),
            )
            .order_by(AssetVersion.created_at.desc(), AssetVersion.version_number.desc())
        )
    )
    by_id = {version.id: version for version in versions}
    current = [version for version in versions if version.is_current]

    def pointed_version(pointer: uuid.UUID | None) -> AssetVersion | None:
        return by_id.get(pointer) if pointer is not None else None

    def first_available(candidates: list[AssetVersion | None], kind: str) -> AssetVersion | None:
        for version in candidates:
            if version is None:
                continue
            preview = preview_file(session, version)
            if preview and preview.media_type.startswith(kind + "/"):
                return version
        return None

    return {
        "audio": first_available(
            [
                pointed_version(project.current_master_asset_version_id),
                pointed_version(project.current_mix_asset_version_id),
                *current,
            ],
            "audio",
        ),
        "artwork": first_available(
            [pointed_version(project.artwork_asset_version_id), *current], "image"
        ),
    }
