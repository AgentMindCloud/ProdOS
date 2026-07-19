from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, String, Text, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from produceros.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin
from produceros.models.enums import (
    ChecklistCategory,
    ChecklistSeverity,
    ChecklistStatus,
    ExplicitStatus,
    ReleaseStatus,
    ReleaseType,
)


class Release(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "releases"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    release_type: Mapped[ReleaseType] = mapped_column(
        SAEnum(ReleaseType, native_enum=False, validate_strings=True), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    release_date: Mapped[date | None] = mapped_column(Date)
    distributor: Mapped[str | None] = mapped_column(String(200))
    isrc: Mapped[str | None] = mapped_column(String(32))
    upc: Mapped[str | None] = mapped_column(String(32))
    explicit_status: Mapped[ExplicitStatus] = mapped_column(
        SAEnum(ExplicitStatus, native_enum=False, validate_strings=True),
        default=ExplicitStatus.NOT_SET,
        nullable=False,
    )
    # Not a ForeignKey: same rationale as Project's asset pointer fields (catalog.py).
    artwork_asset_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ReleaseStatus] = mapped_column(
        SAEnum(ReleaseStatus, native_enum=False, validate_strings=True),
        default=ReleaseStatus.DRAFT,
        nullable=False,
    )
    readiness_status: Mapped[str] = mapped_column(String(20), default="not_started", nullable=False)


class ChecklistRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A single deterministic rule. Default rules are seeded by the
    demo/first-run bootstrap and flagged ``is_system_default`` so they are
    never silently deleted, only deactivated."""

    __tablename__ = "checklist_rules"

    release_type: Mapped[ReleaseType | None] = mapped_column(
        SAEnum(ReleaseType, native_enum=False, validate_strings=True)
    )
    category: Mapped[ChecklistCategory] = mapped_column(
        SAEnum(ChecklistCategory, native_enum=False, validate_strings=True), nullable=False
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(400), nullable=False)
    severity: Mapped[ChecklistSeverity] = mapped_column(
        SAEnum(ChecklistSeverity, native_enum=False, validate_strings=True), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_system_default: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ChecklistResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "checklist_results"

    release_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("releases.id"), nullable=False)
    rule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("checklist_rules.id"), nullable=False)
    status: Mapped[ChecklistStatus] = mapped_column(
        SAEnum(ChecklistStatus, native_enum=False, validate_strings=True), nullable=False
    )
    detail: Mapped[str | None] = mapped_column(Text)
    recommended_action: Mapped[str | None] = mapped_column(Text)
    evaluated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    waived_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    waived_reason: Mapped[str | None] = mapped_column(Text)
