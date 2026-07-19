from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from produceros.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin
from produceros.models.enums import ClearanceStatus, ClearanceType, ContributorRole, RightsShareType


class Contributor(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "contributors"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[ContributorRole] = mapped_column(
        SAEnum(ContributorRole, native_enum=False, validate_strings=True), nullable=False
    )
    email: Mapped[str | None] = mapped_column(String(320))
    pro_affiliation: Mapped[str | None] = mapped_column(String(100))
    ipi_number: Mapped[str | None] = mapped_column(String(32))
    approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class RightsShare(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A single ownership percentage entry.

    Percentages are never modified automatically -- only through an
    explicit, audited user edit. Totals are validated by
    produceros.services.rights but out-of-range totals are only ever
    surfaced as a warning, never auto-corrected.
    """

    __tablename__ = "rights_shares"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    contributor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("contributors.id"))
    holder_name: Mapped[str] = mapped_column(String(200), nullable=False)
    share_type: Mapped[RightsShareType] = mapped_column(
        SAEnum(RightsShareType, native_enum=False, validate_strings=True), nullable=False
    )
    percentage: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class Clearance(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "clearances"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    clearance_type: Mapped[ClearanceType] = mapped_column(
        SAEnum(ClearanceType, native_enum=False, validate_strings=True), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ClearanceStatus] = mapped_column(
        SAEnum(ClearanceStatus, native_enum=False, validate_strings=True),
        default=ClearanceStatus.UNRESOLVED,
        nullable=False,
    )
    rights_holder_contact: Mapped[str | None] = mapped_column(String(300))
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    notes: Mapped[str | None] = mapped_column(Text)
