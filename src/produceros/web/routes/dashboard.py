from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from produceros.models.user import User
from produceros.services.dashboard import build_summary
from produceros.services.media import project_media
from produceros.web.app import templates
from produceros.web.context import base_context
from produceros.web.deps import get_session, require_login

router = APIRouter(tags=["dashboard"])


@router.get("/")
async def dashboard(
    request: Request, session: Session = Depends(get_session), user: User = Depends(require_login)
):
    summary = build_summary(session)
    return templates.TemplateResponse(
        request,
        "dashboard/index.html",
        {
            **base_context(user, "dashboard"),
            "summary": summary,
            "featured": summary.active_projects[0] if summary.active_projects else None,
            "media": project_media(session, summary.active_projects[0])
            if summary.active_projects
            else {"audio": None, "artwork": None},
        },
    )


@router.get("/more")
async def more_menu(request: Request, user: User = Depends(require_login)):
    return templates.TemplateResponse(request, "dashboard/more.html", base_context(user, "more"))
