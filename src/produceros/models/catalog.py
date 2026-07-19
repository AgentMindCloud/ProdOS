from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy import UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from produceros.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin
from produceros.models.enums import (
    ClearanceStatus,
    ExplicitStatus,
    ProjectState,
    ProRegistrationStatus,
    ReleaseType,
)


class Artist(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "artists"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    alias: Mapped[str | None] = mapped_column(String(200))
    bio: Mapped[str | None] = mapped_column(Text)
    contact_email: Mapped[str | None] = mapped_column(String(320))
    notes: Mapped[str | None] = mapped_column(Text)

    projects: Mapped[list["Project"]] = relationship(back_populates="artist")


class Tag(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("name", name="uq_tag_name"),)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str | None] = mapped_column(String(50))


class ProjectTag(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "project_tags"
    __table_args__ = (UniqueConstraint("project_id", "tag_id", name="uq_project_tag"),)

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    tag_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tags.id"), nullable=False)


class Project(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """The central catalog entity. See docs/DATA_MODEL.md for field notes."""

    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("internal_code", name="uq_project_internal_code"),)

    # --- Identity ---
    internal_code: Mapped[str] = mapped_column(String(32), nullable=False)
    working_title: Mapped[str] = mapped_column(String(300), nullable=False)
    final_title: Mapped[str | None] = mapped_column(String(300))
    artist_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("artists.id"))
    producer_name: Mapped[str | None] = mapped_column(String(200))
    featured_artists: Mapped[list] = mapped_column(JSON, default=list)
    alternate_titles: Mapped[list] = mapped_column(JSON, default=list)
    description: Mapped[str | None] = mapped_column(Text)

    # --- Musical information ---
    bpm: Mapped[float | None] = mapped_column(Numeric(6, 2))
    musical_key: Mapped[str | None] = mapped_column(String(16))
    time_signature: Mapped[str] = mapped_column(String(8), default="4/4", nullable=False)
    genre: Mapped[str | None] = mapped_column(String(100))
    subgenre: Mapped[str | None] = mapped_column(String(100))
    mood: Mapped[str | None] = mapped_column(String(100))
    energy: Mapped[int | None] = mapped_column(Integer)  # 1-10 scale
    language: Mapped[str | None] = mapped_column(String(50))
    instruments: Mapped[list] = mapped_column(JSON, default=list)
    vocal_style: Mapped[str | None] = mapped_column(String(200))
    similar_artists: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text)

    # --- Production information ---
    state: Mapped[ProjectState] = mapped_column(
        SAEnum(ProjectState, native_enum=False, validate_strings=True),
        default=ProjectState.IDEA,
        nullable=False,
    )
    fl_project_path: Mapped[str | None] = mapped_column(String(1024))
    fl_project_zip_path: Mapped[str | None] = mapped_column(String(1024))
    project_root_path: Mapped[str | None] = mapped_column(String(1024))
    # NOTE: intentionally *not* a ForeignKey. AssetVersion.asset_id -> Asset.id
    # -> Project.id already forms a chain; adding a reverse FK here would
    # create a three-table circular dependency that SQLite cannot express
    # without deferred/ALTER-based constraints. Referential integrity for
    # these "current pointer" fields is enforced in the service layer
    # (produceros.services.assets) instead.
    current_mix_asset_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    current_master_asset_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    approval_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    revision_notes: Mapped[str | None] = mapped_column(Text)

    # --- Rights information (summary; detail lives in Contributor/RightsShare/Clearance) ---
    split_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sample_clearance_status: Mapped[ClearanceStatus] = mapped_column(
        SAEnum(ClearanceStatus, native_enum=False, validate_strings=True),
        default=ClearanceStatus.NOT_APPLICABLE,
        nullable=False,
    )
    one_stop_clearance_status: Mapped[ClearanceStatus] = mapped_column(
        SAEnum(ClearanceStatus, native_enum=False, validate_strings=True),
        default=ClearanceStatus.NOT_APPLICABLE,
        nullable=False,
    )
    pro_registration_status: Mapped[ProRegistrationStatus] = mapped_column(
        SAEnum(ProRegistrationStatus, native_enum=False, validate_strings=True),
        default=ProRegistrationStatus.NOT_REGISTERED,
        nullable=False,
    )
    master_owner: Mapped[str | None] = mapped_column(String(200))
    composition_owner: Mapped[str | None] = mapped_column(String(200))

    # --- Release information (summary; a Project may have multiple Release rows) ---
    release_type: Mapped[ReleaseType | None] = mapped_column(
        SAEnum(ReleaseType, native_enum=False, validate_strings=True)
    )
    release_date: Mapped[date | None] = mapped_column(Date)
    distributor: Mapped[str | None] = mapped_column(String(200))
    isrc: Mapped[str | None] = mapped_column(String(32))
    upc: Mapped[str | None] = mapped_column(String(32))
    explicit_status: Mapped[ExplicitStatus] = mapped_column(
        SAEnum(ExplicitStatus, native_enum=False, validate_strings=True),
        default=ExplicitStatus.NOT_SET,
        nullable=False,
    )
    artwork_asset_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    release_description: Mapped[str | None] = mapped_column(Text)
    release_readiness_status: Mapped[str] = mapped_column(
        String(20), default="not_started", nullable=False
    )

    artist: Mapped[Artist | None] = relationship(back_populates="projects")
    tracks: Mapped[list["Track"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    versions: Mapped[list["ProjectVersion"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class Track(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tracks"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    track_number: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[float | None] = mapped_column(Numeric(8, 2))
    isrc: Mapped[str | None] = mapped_column(String(32))
    notes: Mapped[str | None] = mapped_column(Text)

    project: Mapped[Project] = relationship(back_populates="tracks")


class ProjectVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A checkpoint in the overall project's evolution (distinct from
    per-asset version history, which lives in ``AssetVersion``)."""

    __tablename__ = "project_versions"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    version_label: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    # Not a ForeignKey for the same reason as Project's asset pointer fields above.
    fl_project_asset_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    created_by_scan: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)

    project: Mapped[Project] = relationship(back_populates="versions")
