"""Scanner roots, scan runs, and finding approval (spec section 9)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from produceros.models.catalog import Project
from produceros.models.enums import AssetType, FindingStatus, FindingType
from produceros.models.scanner import ScannerFinding, ScannerRun
from produceros.models.user import User
from produceros.services import scanner as scanner_service
from produceros.services.assets import approve_finding_as_asset
from produceros.web.app import templates
from produceros.web.context import base_context
from produceros.web.csrf import get_csrf_token, verify_csrf
from produceros.web.deps import get_session, require_login

router = APIRouter(tags=["scanner"], dependencies=[Depends(require_login)])

NEW_VERSION_TYPES = {
    FindingType.NEW_FILE,
    FindingType.NEW_MIX_VERSION,
    FindingType.NEW_MASTER_VERSION,
    FindingType.NEW_PROJECT_VERSION,
}


@router.get("/scanner")
async def scanner_home(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    roots = scanner_service.list_roots(session)
    runs = list(
        session.scalars(select(ScannerRun).order_by(ScannerRun.started_at.desc()).limit(10))
    )
    findings = scanner_service.list_findings(session, status=FindingStatus.NEW)
    projects = list(session.scalars(select(Project).order_by(Project.working_title)))
    csrf_token = get_csrf_token(request)
    return templates.TemplateResponse(
        request,
        "scanner/index.html",
        {
            **base_context(user, "scanner"),
            "roots": roots,
            "runs": runs,
            "findings": findings,
            "projects": projects,
            "asset_types": list(AssetType),
            "new_version_types": {t.value for t in NEW_VERSION_TYPES},
            "csrf_token": csrf_token,
        },
    )


@router.post("/scanner/roots/new")
async def add_root(
    request: Request, session: Session = Depends(get_session), user: User = Depends(require_login)
):
    form = await request.form()
    if verify_csrf(request, form.get("csrf_token")) and form.get("path"):
        scanner_service.add_root(
            session, path=str(form["path"]), label=str(form.get("label") or "") or None
        )
    return RedirectResponse("/scanner", status_code=303)


@router.post("/scanner/roots/{root_id}/deactivate")
async def deactivate_root(
    root_id: str,
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    from produceros.models.scanner import ScannerRoot

    root = session.get(ScannerRoot, uuid.UUID(root_id))
    form = await request.form()
    if root and verify_csrf(request, form.get("csrf_token")):
        scanner_service.deactivate_root(session, root)
    return RedirectResponse("/scanner", status_code=303)


@router.post("/scanner/scan")
async def trigger_scan(
    request: Request, session: Session = Depends(get_session), user: User = Depends(require_login)
):
    form = await request.form()
    if verify_csrf(request, form.get("csrf_token")):
        scanner_service.trigger_scan(session, user_id=user.id)
    return RedirectResponse("/scanner", status_code=303)


@router.post("/scanner/findings/{finding_id}/approve")
async def approve_finding(
    finding_id: str,
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    finding = session.get(ScannerFinding, uuid.UUID(finding_id))
    form = await request.form()
    if (
        finding
        and verify_csrf(request, form.get("csrf_token"))
        and form.get("project_id")
        and form.get("asset_type")
    ):
        project = session.get(Project, uuid.UUID(str(form["project_id"])))
        if project:
            approve_finding_as_asset(
                session,
                finding,
                project=project,
                asset_type=AssetType(str(form["asset_type"])),
                user_id=user.id,
            )
    return RedirectResponse("/scanner", status_code=303)


@router.post("/scanner/findings/{finding_id}/reject")
async def reject_finding(
    finding_id: str,
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    finding = session.get(ScannerFinding, uuid.UUID(finding_id))
    form = await request.form()
    if finding and verify_csrf(request, form.get("csrf_token")):
        scanner_service.reject_finding(session, finding, user_id=user.id)
    return RedirectResponse("/scanner", status_code=303)
