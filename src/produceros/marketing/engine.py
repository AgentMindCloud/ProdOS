"""Draft generation and lifecycle (spec section 13)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from produceros.marketing.context import build_project_context
from produceros.marketing.templates import TEMPLATE_VERSION, render
from produceros.models.catalog import Project
from produceros.models.enums import DraftStatus, MarketingDraftType
from produceros.models.marketing import MarketingDraft
from produceros.models.release import Release
from produceros.services.audit import log_event


def generate_draft(
    session: Session,
    *,
    draft_type: MarketingDraftType,
    project: Project,
    release: Release | None = None,
    campaign_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
) -> MarketingDraft:
    context = build_project_context(session, project, release)
    title, body = render(draft_type, context)

    draft = MarketingDraft(
        campaign_id=campaign_id,
        project_id=project.id,
        draft_type=draft_type,
        title=title,
        body=body,
        status=DraftStatus.DRAFT,
        generated_at=datetime.now(timezone.utc),
        template_version=TEMPLATE_VERSION,
    )
    session.add(draft)
    session.flush()
    log_event(
        session,
        event_type="marketing.draft_generated",
        summary=f"Generated {draft_type.value} draft for '{project.working_title}'.",
        user_id=user_id,
        entity_type="MarketingDraft",
        entity_id=draft.id,
    )
    return draft


def edit_draft(session: Session, draft: MarketingDraft, *, body: str, user_id: uuid.UUID | None = None) -> MarketingDraft:
    draft.body = body
    draft.status = DraftStatus.EDITED
    draft.edited_at = datetime.now(timezone.utc)
    session.flush()
    log_event(
        session,
        event_type="marketing.draft_edited",
        summary=f"Draft '{draft.title}' edited.",
        user_id=user_id,
        entity_type="MarketingDraft",
        entity_id=draft.id,
    )
    return draft


def archive_draft(session: Session, draft: MarketingDraft, *, user_id: uuid.UUID | None = None) -> MarketingDraft:
    draft.status = DraftStatus.ARCHIVED
    session.flush()
    log_event(
        session,
        event_type="marketing.draft_archived",
        summary=f"Draft '{draft.title}' archived.",
        user_id=user_id,
        entity_type="MarketingDraft",
        entity_id=draft.id,
    )
    return draft


def export_draft_as_markdown(draft: MarketingDraft) -> str:
    return f"# {draft.title}\n\n{draft.body}\n"
