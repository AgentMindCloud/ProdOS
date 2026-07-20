"""Releases and release-readiness checklists (spec section 12)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from produceros.models.catalog import Project
from produceros.models.enums import ChecklistCategory, ReleaseType
from produceros.models.release import ChecklistResult, ChecklistRule, Release
from produceros.models.user import User
from produceros.services.checklist import evaluate_release, waive_result
from produceros.web.app import templates
from produceros.web.context import base_context
from produceros.web.csrf import get_csrf_token, verify_csrf
from produceros.web.deps import get_session, require_login

router = APIRouter(tags=["releases"], dependencies=[Depends(require_login)])


@router.get("/releases")
async def list_releases(
    request: Request, session: Session = Depends(get_session), user: User = Depends(require_login)
):
    releases = list(session.scalars(select(Release).order_by(Release.created_at.desc())))
    return templates.TemplateResponse(
        request, "releases/list.html", {**base_context(user, "releases"), "releases": releases}
    )


@router.get("/releases/new")
async def new_release_form(
    request: Request,
    response: Response,
    project_id: str | None = None,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    projects = list(session.scalars(select(Project).order_by(Project.working_title)))
    csrf_token = get_csrf_token(request)
    return templates.TemplateResponse(
        request,
        "releases/new.html",
        {
            **base_context(user, "releases"),
            "projects": projects,
            "release_types": list(ReleaseType),
            "project_id": project_id,
            "csrf_token": csrf_token,
        },
    )


@router.post("/releases/new")
async def create_release(
    request: Request, session: Session = Depends(get_session), user: User = Depends(require_login)
):
    form = await request.form()
    if not verify_csrf(request, form.get("csrf_token")):
        return RedirectResponse("/releases/new", status_code=303)
    project_id = form.get("project_id")
    if not project_id or not form.get("title") or not form.get("release_type"):
        return RedirectResponse("/releases/new", status_code=303)

    release = Release(
        project_id=uuid.UUID(str(project_id)),
        release_type=ReleaseType(str(form["release_type"])),
        title=str(form["title"]),
    )
    session.add(release)
    session.flush()
    evaluate_release(session, release, user_id=user.id)
    return RedirectResponse(f"/releases/{release.id}", status_code=303)


@router.get("/releases/{release_id}")
async def release_detail(
    release_id: str,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    release = session.get(Release, uuid.UUID(release_id))
    if release is None:
        return RedirectResponse("/releases", status_code=303)
    results = list(
        session.scalars(
            select(ChecklistResult)
            .where(ChecklistResult.release_id == release.id)
            .order_by(ChecklistResult.evaluated_at)
        )
    )
    rules_by_id = {r.id: r for r in session.scalars(select(ChecklistRule))}
    grouped: dict[str, list] = {c.value: [] for c in ChecklistCategory}
    for result in results:
        rule = rules_by_id.get(result.rule_id)
        if rule:
            grouped[rule.category.value].append((rule, result))
    project = session.get(Project, release.project_id)
    csrf_token = get_csrf_token(request)
    return templates.TemplateResponse(
        request,
        "releases/detail.html",
        {
            **base_context(user, "releases"),
            "release": release,
            "project": project,
            "grouped": grouped,
            "csrf_token": csrf_token,
        },
    )


@router.post("/releases/{release_id}/evaluate")
async def re_evaluate(
    release_id: str,
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    release = session.get(Release, uuid.UUID(release_id))
    form = await request.form()
    if release and verify_csrf(request, form.get("csrf_token")):
        evaluate_release(session, release, user_id=user.id)
    return RedirectResponse(f"/releases/{release_id}", status_code=303)


@router.post("/checklist-results/{result_id}/waive")
async def waive_checklist_result(
    result_id: str,
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    result = session.get(ChecklistResult, uuid.UUID(result_id))
    form = await request.form()
    if result and verify_csrf(request, form.get("csrf_token")):
        waive_result(
            session,
            result,
            user_id=user.id,
            reason=str(form.get("reason") or "Waived by producer."),
        )
        from produceros.services.checklist import summarize_status

        release = session.get(Release, result.release_id)
        if release is not None:
            all_results = list(
                session.scalars(
                    select(ChecklistResult).where(ChecklistResult.release_id == release.id)
                )
            )
            release.readiness_status = summarize_status(all_results)
            session.flush()
        return RedirectResponse(f"/releases/{result.release_id}", status_code=303)
    return RedirectResponse("/releases", status_code=303)
