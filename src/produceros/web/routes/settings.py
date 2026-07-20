"""Application settings hub (spec sections 7, 11, 18, 21)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from produceros import __version__
from produceros.audio.ffmpeg import ffmpeg_status
from produceros.config import get_settings
from produceros.models.enums import DEFAULT_PROJECT_STATES
from produceros.models.user import User
from produceros.services import settings as settings_service
from produceros.web.app import templates
from produceros.web.context import base_context
from produceros.web.csrf import get_csrf_token, verify_csrf
from produceros.web.deps import get_session, require_login

router = APIRouter(tags=["settings"], dependencies=[Depends(require_login)])


@router.get("/settings")
async def settings_home(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    app_settings = get_settings()
    visible_states = settings_service.get_setting(
        session, settings_service.VISIBLE_PROJECT_STATES_KEY, default=list(DEFAULT_PROJECT_STATES)
    )
    csrf_token = get_csrf_token(request)
    return templates.TemplateResponse(
        request,
        "settings/index.html",
        {
            **base_context(user, "settings"),
            "app_version": __version__,
            "app_env": app_settings.app_env,
            "data_dir": str(app_settings.data_dir),
            "mcp_enabled": app_settings.mcp_enabled,
            "mcp_bind": app_settings.mcp_bind,
            "mcp_port": app_settings.mcp_port,
            "ffmpeg": ffmpeg_status(),
            "all_states": list(DEFAULT_PROJECT_STATES),
            "visible_states": visible_states,
            "csrf_token": csrf_token,
        },
    )


@router.post("/settings/project-states")
async def update_visible_states(
    request: Request, session: Session = Depends(get_session), user: User = Depends(require_login)
):
    form = await request.form()
    if verify_csrf(request, form.get("csrf_token")):
        selected = form.getlist("states") if hasattr(form, "getlist") else []
        # Default system identifiers are always preserved: an empty selection
        # falls back to "all visible" rather than hiding every stage.
        settings_service.set_setting(
            session,
            settings_service.VISIBLE_PROJECT_STATES_KEY,
            selected or list(DEFAULT_PROJECT_STATES),
        )
    return RedirectResponse("/settings", status_code=303)
