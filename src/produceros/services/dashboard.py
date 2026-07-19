"""Aggregates the data shown on the desktop and mobile dashboards
(spec section 17)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from produceros.models.assets import AssetVersion
from produceros.models.calendar import Deadline
from produceros.models.catalog import Project
from produceros.models.enums import DraftStatus, FindingStatus, ProjectState
from produceros.models.marketing import MarketingDraft
from produceros.models.analytics import AnalyticsImport
from produceros.models.release import Release
from produceros.models.rights import RightsShare
from produceros.models.scanner import ScannerFinding
from produceros.models.system import BackupRecord
from produceros.services.rights import validate_rights_shares

INACTIVE_STATES = {ProjectState.RELEASED, ProjectState.ARCHIVED, ProjectState.ON_HOLD}


@dataclass
class DashboardSummary:
    active_project_count: int = 0
    projects_by_stage: dict = field(default_factory=dict)
    active_projects: list = field(default_factory=list)
    releases_needing_attention: list = field(default_factory=list)
    upcoming_deadlines: list = field(default_factory=list)
    unconfirmed_rights_projects: list = field(default_factory=list)
    recent_versions: list = field(default_factory=list)
    recent_findings: list = field(default_factory=list)
    marketing_tasks: list = field(default_factory=list)
    recent_analytics_imports: list = field(default_factory=list)
    last_backup: BackupRecord | None = None


def build_summary(session: Session) -> DashboardSummary:
    summary = DashboardSummary()

    all_projects = list(session.scalars(select(Project)))
    active = [p for p in all_projects if p.state not in INACTIVE_STATES]
    summary.active_project_count = len(active)
    summary.active_projects = sorted(active, key=lambda p: p.updated_at, reverse=True)[:8]

    stage_counts: dict[str, int] = {}
    for p in all_projects:
        stage_counts[p.state.value] = stage_counts.get(p.state.value, 0) + 1
    summary.projects_by_stage = stage_counts

    releases = list(session.scalars(select(Release)))
    summary.releases_needing_attention = [
        r for r in releases if r.readiness_status in ("blocking", "warning")
    ][:8]

    today = date.today()
    deadlines = list(
        session.scalars(
            select(Deadline)
            .where(Deadline.due_date >= today, Deadline.due_date <= today + timedelta(days=14))
            .where(Deadline.completed_at.is_(None), Deadline.cancelled_at.is_(None))
            .order_by(Deadline.due_date)
        )
    )
    summary.upcoming_deadlines = deadlines[:10]

    unconfirmed = []
    for p in active:
        validations = validate_rights_shares(session, p.id)
        if any(v.warning for v in validations) or not validations:
            unconfirmed.append(p)
    summary.unconfirmed_rights_projects = unconfirmed[:8]

    summary.recent_versions = list(
        session.scalars(select(AssetVersion).order_by(AssetVersion.created_at.desc()).limit(8))
    )

    summary.recent_findings = list(
        session.scalars(
            select(ScannerFinding)
            .where(ScannerFinding.status == FindingStatus.NEW)
            .order_by(ScannerFinding.created_at.desc())
            .limit(8)
        )
    )

    summary.marketing_tasks = list(
        session.scalars(
            select(MarketingDraft)
            .where(MarketingDraft.status == DraftStatus.DRAFT)
            .order_by(MarketingDraft.created_at.desc())
            .limit(8)
        )
    )

    summary.recent_analytics_imports = list(
        session.scalars(select(AnalyticsImport).order_by(AnalyticsImport.imported_at.desc()).limit(5))
    )

    summary.last_backup = session.scalar(select(BackupRecord).order_by(BackupRecord.created_at.desc()).limit(1))

    return summary


def summary_to_dict(summary: DashboardSummary) -> dict:
    """A small JSON-safe projection used for the PWA's cached offline
    dashboard summary (spec section 17) -- never live data, just counts
    and titles, refreshed each time the dashboard loads online."""
    return {
        "active_project_count": summary.active_project_count,
        "projects_by_stage": summary.projects_by_stage,
        "active_projects": [{"title": p.working_title, "state": p.state.value} for p in summary.active_projects],
        "upcoming_deadlines": [
            {"title": d.title, "due_date": d.due_date.isoformat()} for d in summary.upcoming_deadlines
        ],
        "releases_needing_attention": len(summary.releases_needing_attention),
    }
