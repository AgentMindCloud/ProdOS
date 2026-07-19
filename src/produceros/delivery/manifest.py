"""Manifest building and completeness validation for delivery packages."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from produceros.models.assets import Asset, AssetVersion
from produceros.models.enums import AssetType
from produceros.models.delivery import DeliveryPreset


@dataclass
class CompletenessCheck:
    asset_type: AssetType
    present: bool
    asset_version_id: uuid.UUID | None


def current_version_for_type(session: Session, project_id: uuid.UUID, asset_type: AssetType) -> AssetVersion | None:
    asset = session.scalar(
        select(Asset).where(Asset.project_id == project_id, Asset.asset_type == asset_type)
    )
    if asset is None:
        return None
    return session.scalar(
        select(AssetVersion).where(AssetVersion.asset_id == asset.id, AssetVersion.is_current.is_(True))
    )


def check_completeness(session: Session, project_id: uuid.UUID, preset: DeliveryPreset) -> list[CompletenessCheck]:
    results = []
    for raw_type in preset.required_asset_types:
        asset_type = AssetType(raw_type)
        version = current_version_for_type(session, project_id, asset_type)
        results.append(
            CompletenessCheck(asset_type=asset_type, present=version is not None, asset_version_id=version.id if version else None)
        )
    return results
