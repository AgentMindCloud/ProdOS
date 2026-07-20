"""Delivery preset definitions (spec section 15)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from produceros.models.delivery import DeliveryPreset
from produceros.models.enums import AssetType, DeliveryPresetType


@dataclass
class PresetDefinition:
    name: str
    preset_type: DeliveryPresetType
    required_asset_types: list[AssetType]


DEFAULT_PRESETS: list[PresetDefinition] = [
    PresetDefinition(
        name="Client Package",
        preset_type=DeliveryPresetType.CLIENT,
        required_asset_types=[
            AssetType.MIX,
            AssetType.MASTER,
            AssetType.INSTRUMENTAL,
            AssetType.ACAPELLA,
            AssetType.STEMS,
        ],
    ),
    PresetDefinition(
        name="Sync Package",
        preset_type=DeliveryPresetType.SYNC,
        required_asset_types=[
            AssetType.MASTER,
            AssetType.INSTRUMENTAL,
            AssetType.CLEAN_VERSION,
            AssetType.NO_DRUMS,
            AssetType.NO_VOCALS,
            AssetType.STEMS,
            AssetType.LYRICS,
        ],
    ),
    PresetDefinition(
        name="Distributor Package",
        preset_type=DeliveryPresetType.DISTRIBUTOR,
        required_asset_types=[AssetType.MASTER, AssetType.ARTWORK],
    ),
]


def seed_default_presets(session: Session) -> None:
    existing_names = set(session.scalars(select(DeliveryPreset.name)))
    for definition in DEFAULT_PRESETS:
        if definition.name in existing_names:
            continue
        session.add(
            DeliveryPreset(
                name=definition.name,
                preset_type=definition.preset_type,
                required_asset_types=[t.value for t in definition.required_asset_types],
                is_system_default=True,
            )
        )
    session.flush()
