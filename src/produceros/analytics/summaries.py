"""Deterministic analytics summaries (spec section 16).

No hit prediction, no causal claims -- these are plain aggregations over
manually imported/entered numbers, with explicit missing-data warnings
where a period or channel is incomplete.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from produceros.models.analytics import AnalyticsImport, AnalyticsMetric
from produceros.models.enums import AnalyticsMetricType

COST_METRICS = {AnalyticsMetricType.ADVERTISING_SPEND}
REVENUE_METRICS = {AnalyticsMetricType.REVENUE, AnalyticsMetricType.BEAT_SALES, AnalyticsMetricType.LICENSING_REVENUE}


@dataclass
class MetricTotal:
    metric_type: str
    total: float


def _metrics_for(session: Session, *, project_id: uuid.UUID | None = None, campaign_id: uuid.UUID | None = None) -> list[AnalyticsMetric]:
    stmt = select(AnalyticsMetric).join(AnalyticsImport, AnalyticsMetric.import_id == AnalyticsImport.id)
    if project_id:
        stmt = stmt.where(AnalyticsImport.project_id == project_id)
    if campaign_id:
        stmt = stmt.where(AnalyticsImport.campaign_id == campaign_id)
    return list(session.scalars(stmt))


def release_summary(session: Session, project_id: uuid.UUID) -> list[MetricTotal]:
    totals: dict[str, float] = defaultdict(float)
    for metric in _metrics_for(session, project_id=project_id):
        totals[metric.metric_type.value] += float(metric.value)
    return [MetricTotal(metric_type=k, total=v) for k, v in sorted(totals.items())]


def campaign_summary(session: Session, campaign_id: uuid.UUID) -> list[MetricTotal]:
    totals: dict[str, float] = defaultdict(float)
    for metric in _metrics_for(session, campaign_id=campaign_id):
        totals[metric.metric_type.value] += float(metric.value)
    return [MetricTotal(metric_type=k, total=v) for k, v in sorted(totals.items())]


def channel_summary(session: Session, *, project_id: uuid.UUID | None = None) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for metric in _metrics_for(session, project_id=project_id):
        channel = metric.channel or "Unspecified"
        totals[channel] += float(metric.value)
    return dict(sorted(totals.items(), key=lambda kv: -kv[1]))


def content_performance_ranking(session: Session, *, project_id: uuid.UUID | None = None) -> list[tuple[str, float]]:
    totals: dict[str, float] = defaultdict(float)
    for metric in _metrics_for(session, project_id=project_id):
        if not metric.content_reference:
            continue
        totals[metric.content_reference] += float(metric.value)
    return sorted(totals.items(), key=lambda kv: -kv[1])


def cost_summary(session: Session, *, project_id: uuid.UUID | None = None) -> float:
    return sum(
        float(m.value) for m in _metrics_for(session, project_id=project_id) if m.metric_type in COST_METRICS
    )


def revenue_summary(session: Session, *, project_id: uuid.UUID | None = None) -> float:
    return sum(
        float(m.value) for m in _metrics_for(session, project_id=project_id) if m.metric_type in REVENUE_METRICS
    )


def missing_data_warnings(session: Session, imports: list[AnalyticsImport]) -> list[str]:
    warnings: list[str] = []
    for imp in imports:
        warnings.extend(f"Import {imp.id} ({imp.original_filename or 'manual entry'}): {w}" for w in imp.warnings)
    return warnings
