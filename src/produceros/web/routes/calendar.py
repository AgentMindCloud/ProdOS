"""Release calendar and .ics export (spec section 14)."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import PlainTextResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from produceros.models.catalog import Artist, Project
from produceros.models.enums import DeadlineType
from produceros.models.marketing import MarketingCampaign
from produceros.models.user import User
from produceros.services.calendar import create_deadline, export_ics, list_deadlines, overdue
from produceros.web.app import templates
from produceros.web.context import base_context
from produceros.web.csrf import get_csrf_token, verify_csrf
from produceros.web.deps import get_session, require_login

router = APIRouter(tags=["calendar"], dependencies=[Depends(require_login)])


@router.get("/calendar")
async def calendar_home(
    request: Request, response: Response, session: Session = Depends(get_session), user: User = Depends(require_login),
    project_id: str | None = None, artist_id: str | None = None, campaign_id: str | None = None, deadline_type: str | None = None,
):
    filters = dict(
        project_id=uuid.UUID(project_id) if project_id else None,
        artist_id=uuid.UUID(artist_id) if artist_id else None,
        campaign_id=uuid.UUID(campaign_id) if campaign_id else None,
        deadline_type=DeadlineType(deadline_type) if deadline_type else None,
    )
    today = date.today()
    upcoming = list_deadlines(session, start=today, end=today + timedelta(days=90), include_done=False, **filters)
    overdue_items = overdue(session, **filters)
    projects = list(session.scalars(select(Project).order_by(Project.working_title)))
    artists = list(session.scalars(select(Artist).order_by(Artist.name)))
    campaigns = list(session.scalars(select(MarketingCampaign).order_by(MarketingCampaign.name)))
    csrf_token = get_csrf_token(request)
    return templates.TemplateResponse(
        request, "calendar/index.html",
        {
            **base_context(user, "calendar"),
            "upcoming": upcoming, "overdue_items": overdue_items,
            "projects": projects, "artists": artists, "campaigns": campaigns,
            "deadline_types": list(DeadlineType),
            "csrf_token": csrf_token,
        },
    )


@router.post("/calendar/deadlines/new")
async def new_deadline(request: Request, session: Session = Depends(get_session), user: User = Depends(require_login)):
    form = await request.form()
    if verify_csrf(request, form.get("csrf_token")) and form.get("title") and form.get("due_date") and form.get("deadline_type"):
        create_deadline(
            session, title=str(form["title"]), deadline_type=DeadlineType(form["deadline_type"]),
            due_date=date.fromisoformat(str(form["due_date"])),
            project_id=uuid.UUID(str(form["project_id"])) if form.get("project_id") else None,
            artist_id=uuid.UUID(str(form["artist_id"])) if form.get("artist_id") else None,
            campaign_id=uuid.UUID(str(form["campaign_id"])) if form.get("campaign_id") else None,
            user_id=user.id,
        )
    return RedirectResponse("/calendar", status_code=303)


@router.post("/calendar/deadlines/{deadline_id}/complete")
async def complete_deadline_route(deadline_id: str, request: Request, session: Session = Depends(get_session), user: User = Depends(require_login)):
    from produceros.models.calendar import Deadline
    from produceros.services.calendar import complete_deadline

    deadline = session.get(Deadline, uuid.UUID(deadline_id))
    form = await request.form()
    if deadline and verify_csrf(request, form.get("csrf_token")):
        complete_deadline(session, deadline, user_id=user.id)
    return RedirectResponse("/calendar", status_code=303)


@router.get("/calendar/export.ics")
async def export_calendar(request: Request, session: Session = Depends(get_session), user: User = Depends(require_login)):
    deadlines = list_deadlines(session, include_done=False)
    ics_content = export_ics(deadlines)
    return PlainTextResponse(ics_content, media_type="text/calendar", headers={"Content-Disposition": 'attachment; filename="produceros-calendar.ics"'})
