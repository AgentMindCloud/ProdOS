from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from produceros.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from produceros.models.enums import AnalyticsMetricType, AnalyticsSourceType, RawOrCalculated


class AnalyticsSource(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "analytics_sources"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[AnalyticsSourceType] = mapped_column(
        SAEnum(AnalyticsSourceType, native_enum=False, validate_strings=True), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)


class AnalyticsImport(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "analytics_imports"

    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analytics_sources.id"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"))
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("marketing_campaigns.id"))
    reporting_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    reporting_period_end: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    raw_or_calculated: Mapped[RawOrCalculated] = mapped_column(
        SAEnum(RawOrCalculated, native_enum=False, validate_strings=True),
        default=RawOrCalculated.RAW,
        nullable=False,
    )
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    imported_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    original_filename: Mapped[str | None] = mapped_column(String(500))
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warnings: Mapped[list] = mapped_column(JSON, default=list)


class AnalyticsMetric(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "analytics_metrics"

    import_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analytics_imports.id"), nullable=False
    )
    metric_type: Mapped[AnalyticsMetricType] = mapped_column(
        SAEnum(AnalyticsMetricType, native_enum=False, validate_strings=True), nullable=False
    )
    value: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    channel: Mapped[str | None] = mapped_column(String(100))
    content_reference: Mapped[str | None] = mapped_column(String(300))
