from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from produceros.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin
from produceros.models.enums import DeliveryPackageStatus, DeliveryPresetType


class DeliveryPreset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "delivery_presets"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    preset_type: Mapped[DeliveryPresetType] = mapped_column(
        SAEnum(DeliveryPresetType, native_enum=False, validate_strings=True), nullable=False
    )
    required_asset_types: Mapped[list] = mapped_column(JSON, default=list)  # list[AssetType]
    is_system_default: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class DeliveryPackage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "delivery_packages"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    preset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("delivery_presets.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[DeliveryPackageStatus] = mapped_column(
        SAEnum(DeliveryPackageStatus, native_enum=False, validate_strings=True),
        default=DeliveryPackageStatus.DRAFT,
        nullable=False,
    )
    output_directory: Mapped[str | None] = mapped_column(String(1024))
    manifest_generated_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    notes: Mapped[str | None] = mapped_column(Text)

    items: Mapped[list[DeliveryManifestItem]] = relationship(
        back_populates="package", cascade="all, delete-orphan"
    )


class DeliveryManifestItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "delivery_manifest_items"

    package_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("delivery_packages.id"), nullable=False
    )
    asset_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("asset_versions.id"))
    role_in_package: Mapped[str] = mapped_column(String(200), nullable=False)
    source_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    destination_relative_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    copied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    package: Mapped[DeliveryPackage] = relationship(back_populates="items")
