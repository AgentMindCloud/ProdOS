"""Analytics import persistence (spec section 16)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from produceros.analytics.importer import ParseResult
from produceros.models.analytics import AnalyticsImport, AnalyticsMetric, AnalyticsSource
from produceros.models.enums import AnalyticsMetricType, AnalyticsSourceType, RawOrCalculated
from produceros.services.audit import log_event


def get_or_create_source(
    session: Session, name: str, source_type: AnalyticsSourceType
) -> AnalyticsSource:
    source = session.scalar(select(AnalyticsSource).where(AnalyticsSource.name == name))
    if source is None:
        source = AnalyticsSource(name=name, source_type=source_type)
        session.add(source)
        session.flush()
    return source


def record_import(
    session: Session,
    *,
    source: AnalyticsSource,
    parsed: ParseResult,
    reporting_period_start: date,
    reporting_period_end: date,
    currency: str = "USD",
    raw_or_calculated: RawOrCalculated = RawOrCalculated.RAW,
    project_id: uuid.UUID | None = None,
    campaign_id: uuid.UUID | None = None,
    original_filename: str | None = None,
    user_id: uuid.UUID | None = None,
) -> AnalyticsImport:
    import_row = AnalyticsImport(
        source_id=source.id,
        project_id=project_id,
        campaign_id=campaign_id,
        reporting_period_start=reporting_period_start,
        reporting_period_end=reporting_period_end,
        currency=currency,
        raw_or_calculated=raw_or_calculated,
        imported_at=datetime.now(UTC),
        imported_by=user_id,
        original_filename=original_filename,
        row_count=len(parsed.rows),
        warnings=parsed.warnings,
    )
    session.add(import_row)
    session.flush()

    for row in parsed.rows:
        session.add(
            AnalyticsMetric(
                import_id=import_row.id,
                metric_type=AnalyticsMetricType(row.metric_type),
                value=row.value,
                channel=row.channel,
                content_reference=row.content_reference,
            )
        )
    session.flush()

    log_event(
        session,
        event_type="analytics.import_recorded",
        summary=f"Imported {len(parsed.rows)} analytics row(s) from '{source.name}' ({len(parsed.warnings)} warning(s)).",
        user_id=user_id,
        entity_type="AnalyticsImport",
        entity_id=import_row.id,
    )
    return import_row


def add_manual_metric(
    session: Session,
    *,
    source: AnalyticsSource,
    metric_type: AnalyticsMetricType,
    value: float,
    reporting_period_start: date,
    reporting_period_end: date,
    project_id: uuid.UUID | None = None,
    campaign_id: uuid.UUID | None = None,
    channel: str | None = None,
    content_reference: str | None = None,
    user_id: uuid.UUID | None = None,
) -> AnalyticsMetric:
    import_row = AnalyticsImport(
        source_id=source.id,
        project_id=project_id,
        campaign_id=campaign_id,
        reporting_period_start=reporting_period_start,
        reporting_period_end=reporting_period_end,
        raw_or_calculated=RawOrCalculated.RAW,
        imported_at=datetime.now(UTC),
        imported_by=user_id,
        row_count=1,
        warnings=[],
    )
    session.add(import_row)
    session.flush()
    metric = AnalyticsMetric(
        import_id=import_row.id,
        metric_type=metric_type,
        value=value,
        channel=channel,
        content_reference=content_reference,
    )
    session.add(metric)
    session.flush()
    log_event(
        session,
        event_type="analytics.manual_metric_added",
        summary=f"Manually recorded {metric_type.value} = {value}.",
        user_id=user_id,
        entity_type="AnalyticsMetric",
        entity_id=metric.id,
    )
    return metric
