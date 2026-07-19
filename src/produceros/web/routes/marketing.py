"""Marketing campaigns, content assets, and template-based drafts
(spec section 13)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import PlainTextResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from produceros.marketing.campaigns import create_campaign, create_content_asset, list_campaigns, list_content_assets
from produceros.marketing.engine import archive_draft, edit_draft, export_draft_as_markdown, generate_draft
from produceros.models.catalog import Project
from produceros.models.enums import CampaignType, ContentAssetType, MarketingDraftType
from produceros.models.marketing import MarketingDraft
from produceros.models.user import User
from produceros.web.app import templates
from produceros.web.context import base_context
from produceros.web.csrf import get_csrf_token, verify_csrf
from produceros.web.deps import get_session, require_login

router = APIRouter(tags=["marketing"], dependencies=[Depends(require_login)])


@router.get("/marketing")
async def marketing_home(request: Request, response: Response, session: Session = Depends(get_session), user: User = Depends(require_login)):
    campaigns = list_campaigns(session)
    drafts = list(session.scalars(select(MarketingDraft).order_by(MarketingDraft.created_at.desc()).limit(30)))
    content_assets = list_content_assets(session)
    projects = list(session.scalars(select(Project).order_by(Project.working_title)))
    csrf_token = get_csrf_token(request)
    return templates.TemplateResponse(
        request, "marketing/index.html",
        {
            **base_context(user, "marketing"),
            "campaigns": campaigns, "drafts": drafts, "content_assets": content_assets, "projects": projects,
            "campaign_types": list(CampaignType), "draft_types": list(MarketingDraftType), "content_types": list(ContentAssetType),
            "csrf_token": csrf_token,
        },
    )


@router.post("/marketing/campaigns/new")
async def new_campaign(request: Request, session: Session = Depends(get_session), user: User = Depends(require_login)):
    form = await request.form()
    if verify_csrf(request, form.get("csrf_token")) and form.get("name"):
        create_campaign(
            session, name=str(form["name"]), campaign_type=CampaignType(form.get("campaign_type") or "custom"),
            project_id=uuid.UUID(str(form["project_id"])) if form.get("project_id") else None, user_id=user.id,
        )
    return RedirectResponse("/marketing", status_code=303)


@router.post("/marketing/content-assets/new")
async def new_content_asset(request: Request, session: Session = Depends(get_session), user: User = Depends(require_login)):
    form = await request.form()
    if verify_csrf(request, form.get("csrf_token")) and form.get("title") and form.get("content_type"):
        create_content_asset(
            session, title=str(form["title"]), content_type=ContentAssetType(form["content_type"]),
            project_id=uuid.UUID(str(form["project_id"])) if form.get("project_id") else None,
        )
    return RedirectResponse("/marketing", status_code=303)


@router.post("/marketing/drafts/generate")
async def generate_marketing_draft(request: Request, session: Session = Depends(get_session), user: User = Depends(require_login)):
    form = await request.form()
    if verify_csrf(request, form.get("csrf_token")) and form.get("project_id") and form.get("draft_type"):
        project = session.get(Project, uuid.UUID(str(form["project_id"])))
        if project:
            draft = generate_draft(session, draft_type=MarketingDraftType(form["draft_type"]), project=project, user_id=user.id)
            return RedirectResponse(f"/marketing/drafts/{draft.id}", status_code=303)
    return RedirectResponse("/marketing", status_code=303)


@router.get("/marketing/drafts/{draft_id}")
async def draft_detail(draft_id: str, request: Request, response: Response, session: Session = Depends(get_session), user: User = Depends(require_login)):
    draft = session.get(MarketingDraft, uuid.UUID(draft_id))
    if draft is None:
        return RedirectResponse("/marketing", status_code=303)
    csrf_token = get_csrf_token(request)
    return templates.TemplateResponse(request, "marketing/draft_detail.html", {**base_context(user, "marketing"), "draft": draft, "csrf_token": csrf_token})


@router.post("/marketing/drafts/{draft_id}/edit")
async def edit_marketing_draft(draft_id: str, request: Request, session: Session = Depends(get_session), user: User = Depends(require_login)):
    draft = session.get(MarketingDraft, uuid.UUID(draft_id))
    form = await request.form()
    if draft and verify_csrf(request, form.get("csrf_token")):
        edit_draft(session, draft, body=str(form.get("body") or ""), user_id=user.id)
    return RedirectResponse(f"/marketing/drafts/{draft_id}", status_code=303)


@router.post("/marketing/drafts/{draft_id}/archive")
async def archive_marketing_draft(draft_id: str, request: Request, session: Session = Depends(get_session), user: User = Depends(require_login)):
    draft = session.get(MarketingDraft, uuid.UUID(draft_id))
    form = await request.form()
    if draft and verify_csrf(request, form.get("csrf_token")):
        archive_draft(session, draft, user_id=user.id)
    return RedirectResponse("/marketing", status_code=303)


@router.get("/marketing/drafts/{draft_id}/export")
async def export_marketing_draft(draft_id: str, session: Session = Depends(get_session), user: User = Depends(require_login)):
    draft = session.get(MarketingDraft, uuid.UUID(draft_id))
    if draft is None:
        return RedirectResponse("/marketing", status_code=303)
    content = export_draft_as_markdown(draft)
    filename = f"{draft.draft_type.value}-{draft.id}.md"
    return PlainTextResponse(content, media_type="text/markdown", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
