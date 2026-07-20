"""MCP tool implementations (spec section 21).

Every function here is read-only or draft-only: none of them delete a
file, publish a release, send a message, or expose a secret. Each is a
plain function of a SQLAlchemy session so it can be unit-tested directly,
independent of the MCP transport in ``produceros.mcp_server.server``.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from produceros.marketing.campaigns import list_campaigns
from produceros.marketing.engine import generate_draft
from produceros.models.assets import Asset, AssetVersion
from produceros.models.catalog import Project
from produceros.models.enums import MarketingDraftType, ReleaseType
from produceros.models.marketing import MarketingDraft
from produceros.models.release import Release
from produceros.services.calendar import list_deadlines
from produceros.services.catalog import list_projects
from produceros.services.checklist import evaluate_release


def _project_summary(project: Project) -> dict:
    return {
        "id": str(project.id),
        "internal_code": project.internal_code,
        "working_title": project.working_title,
        "final_title": project.final_title,
        "artist": project.artist.name if project.artist else None,
        "state": project.state.value,
        "genre": project.genre,
        "mood": project.mood,
        "bpm": float(project.bpm) if project.bpm is not None else None,
        "musical_key": project.musical_key,
    }


def search_projects(session: Session, query: str) -> list[dict]:
    return [_project_summary(p) for p in list_projects(session, search=query)]


def get_project(session: Session, project_id: str) -> dict | None:
    from produceros.models.catalog import ProjectTag, Tag

    project = session.get(Project, uuid.UUID(project_id))
    if project is None:
        return None
    tags = session.scalars(
        select(Tag.name)
        .join(ProjectTag, ProjectTag.tag_id == Tag.id)
        .where(ProjectTag.project_id == project.id)
    )
    summary = _project_summary(project)
    summary.update(
        {
            "description": project.description,
            "subgenre": project.subgenre,
            "energy": project.energy,
            "language": project.language,
            "instruments": project.instruments,
            "tags": list(tags),
            "release_readiness_status": project.release_readiness_status,
            "notes": project.notes,
        }
    )
    return summary


def list_active_projects(session: Session) -> list[dict]:
    from produceros.services.dashboard import INACTIVE_STATES

    return [_project_summary(p) for p in list_projects(session) if p.state not in INACTIVE_STATES]


def list_recent_versions(session: Session, limit: int = 10) -> list[dict]:
    versions = session.scalars(
        select(AssetVersion).order_by(AssetVersion.created_at.desc()).limit(limit)
    )
    return [
        {
            "id": str(v.id),
            "asset_id": str(v.asset_id),
            "original_filename": v.original_filename,
            "version_number": v.version_number,
            "is_current": v.is_current,
            "approval_status": v.approval_status.value,
        }
        for v in versions
    ]


def find_missing_assets(session: Session) -> list[dict]:
    """Assets (mix/master/etc. "slots") that have never had a current
    version registered, across all projects."""
    results = []
    assets = session.scalars(select(Asset))
    for asset in assets:
        has_current = session.scalar(
            select(AssetVersion).where(
                AssetVersion.asset_id == asset.id, AssetVersion.is_current.is_(True)
            )
        )
        if has_current is None:
            project = session.get(Project, asset.project_id)
            results.append(
                {
                    "project_id": str(asset.project_id),
                    "project_title": project.working_title if project else None,
                    "asset_type": asset.asset_type.value,
                    "asset_label": asset.label,
                }
            )
    return results


def check_release_readiness(session: Session, release_id: str) -> dict | None:
    release = session.get(Release, uuid.UUID(release_id))
    if release is None:
        return None
    results = evaluate_release(session, release)
    return {
        "release_id": str(release.id),
        "title": release.title,
        "readiness_status": release.readiness_status,
        "checks": [{"status": r.status.value, "detail": r.detail} for r in results],
    }


def list_upcoming_deadlines(session: Session, days: int = 30) -> list[dict]:
    today = date.today()
    deadlines = list_deadlines(
        session, start=today, end=today + timedelta(days=days), include_done=False
    )
    return [
        {
            "id": str(d.id),
            "title": d.title,
            "due_date": d.due_date.isoformat(),
            "type": d.deadline_type.value,
        }
        for d in deadlines
    ]


def search_catalog_by_mood(session: Session, mood: str) -> list[dict]:
    stmt = select(Project).where(Project.mood.ilike(f"%{mood}%"))
    return [_project_summary(p) for p in session.scalars(stmt)]


def search_catalog_by_bpm(session: Session, min_bpm: float, max_bpm: float) -> list[dict]:
    stmt = select(Project).where(
        Project.bpm.is_not(None), Project.bpm >= min_bpm, Project.bpm <= max_bpm
    )
    return [_project_summary(p) for p in session.scalars(stmt)]


def search_catalog_by_key(session: Session, musical_key: str) -> list[dict]:
    stmt = select(Project).where(Project.musical_key.ilike(musical_key))
    return [_project_summary(p) for p in session.scalars(stmt)]


def get_marketing_plan(session: Session, project_id: str) -> dict | None:
    project = session.get(Project, uuid.UUID(project_id))
    if project is None:
        return None
    campaigns = list_campaigns(session, project_id=project.id)
    drafts = session.scalars(select(MarketingDraft).where(MarketingDraft.project_id == project.id))
    return {
        "project_id": str(project.id),
        "campaigns": [
            {"id": str(c.id), "name": c.name, "status": c.status.value} for c in campaigns
        ],
        "drafts": [
            {
                "id": str(d.id),
                "type": d.draft_type.value,
                "title": d.title,
                "status": d.status.value,
            }
            for d in drafts
        ],
    }


def create_marketing_draft(session: Session, project_id: str, draft_type: str) -> dict | None:
    project = session.get(Project, uuid.UUID(project_id))
    if project is None:
        return None
    draft = generate_draft(session, draft_type=MarketingDraftType(draft_type), project=project)
    return {
        "id": str(draft.id),
        "title": draft.title,
        "body": draft.body,
        "status": draft.status.value,
    }


def create_release_checklist_draft(
    session: Session, project_id: str, release_type: str, title: str
) -> dict | None:
    project = session.get(Project, uuid.UUID(project_id))
    if project is None:
        return None
    release = Release(project_id=project.id, release_type=ReleaseType(release_type), title=title)
    session.add(release)
    session.flush()
    results = evaluate_release(session, release)
    return {
        "release_id": str(release.id),
        "readiness_status": release.readiness_status,
        "checks": [{"status": r.status.value, "detail": r.detail} for r in results],
    }


def create_sync_pitch_draft(session: Session, project_id: str) -> dict | None:
    return create_marketing_draft(session, project_id, MarketingDraftType.SYNC_PITCH.value)
