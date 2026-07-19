from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from produceros.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin
from produceros.models.enums import (
    ApprovalStatus,
    AssetRegisteredVia,
    AssetType,
    MetadataConfidence,
)


class Asset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A named "slot" for one category of deliverable within a project
    (e.g. "Master", "Instrumental", "Stems Package"). Each Asset owns a
    history of ``AssetVersion`` rows; at most one is marked current."""

    __tablename__ = "assets"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    track_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tracks.id"))
    asset_type: Mapped[AssetType] = mapped_column(
        SAEnum(AssetType, native_enum=False, validate_strings=True), nullable=False
    )
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    versions: Mapped[list["AssetVersion"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan", order_by="AssetVersion.version_number"
    )


class AssetVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One concrete, hash-identified file registered under an Asset slot.

    Historical versions are never overwritten or deleted by ProducerOS;
    only ``is_current`` moves between versions of the same Asset.
    """

    __tablename__ = "asset_versions"

    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assets.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    full_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    modified_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    parsed_artist: Mapped[str | None] = mapped_column(String(200))
    parsed_track: Mapped[str | None] = mapped_column(String(300))
    parsed_mix_or_master: Mapped[str | None] = mapped_column(String(20))
    parsed_version_label: Mapped[str | None] = mapped_column(String(50))
    parsed_date: Mapped[date | None] = mapped_column(Date)
    parsed_bpm: Mapped[float | None] = mapped_column(Numeric(6, 2))
    parsed_key: Mapped[str | None] = mapped_column(String(16))
    parsed_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    approval_status: Mapped[ApprovalStatus] = mapped_column(
        SAEnum(ApprovalStatus, native_enum=False, validate_strings=True),
        default=ApprovalStatus.PENDING,
        nullable=False,
    )
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    registered_via: Mapped[AssetRegisteredVia] = mapped_column(
        SAEnum(AssetRegisteredVia, native_enum=False, validate_strings=True),
        default=AssetRegisteredVia.MANUAL,
        nullable=False,
    )

    asset: Mapped[Asset] = relationship(back_populates="versions")
    analysis: Mapped["AudioAnalysis | None"] = relationship(
        back_populates="asset_version", cascade="all, delete-orphan", uselist=False
    )


class AudioAnalysis(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Extracted/measured audio metadata for one AssetVersion.

    ``confirmed_bpm`` / ``confirmed_key`` are the only fields a user edit
    is allowed to set directly; automated re-analysis never overwrites
    them (see produceros.audio.metadata precedence rules).
    """

    __tablename__ = "audio_analyses"

    asset_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("asset_versions.id"), unique=True, nullable=False
    )
    file_type: Mapped[str | None] = mapped_column(String(20))
    duration_seconds: Mapped[float | None] = mapped_column(Numeric(10, 3))
    sample_rate: Mapped[int | None] = mapped_column(Integer)
    bit_depth: Mapped[int | None] = mapped_column(Integer)
    channels: Mapped[int | None] = mapped_column(Integer)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)

    embedded_title: Mapped[str | None] = mapped_column(String(300))
    embedded_artist: Mapped[str | None] = mapped_column(String(200))
    embedded_album: Mapped[str | None] = mapped_column(String(300))
    embedded_track_number: Mapped[str | None] = mapped_column(String(20))

    integrated_loudness_lufs: Mapped[float | None] = mapped_column(Numeric(6, 2))
    loudness_range_lu: Mapped[float | None] = mapped_column(Numeric(6, 2))
    true_peak_dbfs: Mapped[float | None] = mapped_column(Numeric(6, 2))
    peak_level_dbfs: Mapped[float | None] = mapped_column(Numeric(6, 2))
    codec_info: Mapped[str | None] = mapped_column(String(200))
    ffmpeg_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    confirmed_bpm: Mapped[float | None] = mapped_column(Numeric(6, 2))
    confirmed_key: Mapped[str | None] = mapped_column(String(16))
    bpm_source: Mapped[MetadataConfidence | None] = mapped_column(
        SAEnum(MetadataConfidence, native_enum=False, validate_strings=True)
    )
    key_source: Mapped[MetadataConfidence | None] = mapped_column(
        SAEnum(MetadataConfidence, native_enum=False, validate_strings=True)
    )

    analyzed_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    warnings: Mapped[list] = mapped_column(JSON, default=list)

    asset_version: Mapped[AssetVersion] = relationship(back_populates="analysis")
