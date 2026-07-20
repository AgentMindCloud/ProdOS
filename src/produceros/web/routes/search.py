"""Global search and saved filters (spec section 23)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from produceros.models.user import User
from produceros.services.search import (
    delete_saved_filter,
    global_search,
    list_saved_filters,
    save_filter,
)
from produceros.web.app import templates
from produceros.web.context import base_context
from produceros.web.csrf import get_csrf_token, verify_csrf
from produceros.web.deps import get_session, require_login

router = APIRouter(tags=["search"], dependencies=[Depends(require_login)])


@router.get("/search")
async def search_page(
    request: Request,
    response: Response,
    q: str = "",
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    results = (
        global_search(session, q) if q.strip() else {"projects": [], "artists": [], "releases": []}
    )
    saved_filters = list_saved_filters(session)
    csrf_token = get_csrf_token(request)
    return templates.TemplateResponse(
        request,
        "search/index.html",
        {
            **base_context(user, ""),
            "query": q,
            "results": results,
            "saved_filters": saved_filters,
            "csrf_token": csrf_token,
        },
    )


@router.post("/search/saved-filters/new")
async def new_saved_filter(
    request: Request, session: Session = Depends(get_session), user: User = Depends(require_login)
):
    form = await request.form()
    if verify_csrf(request, form.get("csrf_token")) and form.get("name") and form.get("query"):
        save_filter(session, str(form["name"]), str(form["query"]))
    return RedirectResponse(f"/search?q={form.get('query', '')}", status_code=303)


@router.post("/search/saved-filters/{key}/delete")
async def delete_saved_filter_route(
    key: str,
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    form = await request.form()
    if verify_csrf(request, form.get("csrf_token")):
        delete_saved_filter(session, key)
    return RedirectResponse("/search", status_code=303)
