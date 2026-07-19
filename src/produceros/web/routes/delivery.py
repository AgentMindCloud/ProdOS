"""Delivery packages (spec section 15)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from produceros.delivery.manifest import check_completeness
from produceros.delivery.packaging import approve_package, create_package, execute_package, generate_manifest
from produceros.delivery.presets import seed_default_presets
from produceros.models.catalog import Project
from produceros.models.delivery import DeliveryPackage, DeliveryPreset
from produceros.models.user import User
from produceros.web.app import templates
from produceros.web.context import base_context
from produceros.web.csrf import get_csrf_token, verify_csrf
from produceros.web.deps import get_session, require_login

router = APIRouter(tags=["delivery"], dependencies=[Depends(require_login)])


@router.get("/delivery")
async def delivery_home(request: Request, response: Response, session: Session = Depends(get_session), user: User = Depends(require_login)):
    seed_default_presets(session)
    packages = list(session.scalars(select(DeliveryPackage).order_by(DeliveryPackage.created_at.desc())))
    presets = list(session.scalars(select(DeliveryPreset)))
    projects = list(session.scalars(select(Project).order_by(Project.working_title)))
    csrf_token = get_csrf_token(request)
    return templates.TemplateResponse(
        request, "delivery/index.html",
        {**base_context(user, "delivery"), "packages": packages, "presets": presets, "projects": projects, "csrf_token": csrf_token},
    )


@router.post("/delivery/packages/new")
async def new_package(request: Request, session: Session = Depends(get_session), user: User = Depends(require_login)):
    form = await request.form()
    if verify_csrf(request, form.get("csrf_token")) and form.get("project_id") and form.get("preset_id") and form.get("output_directory"):
        project = session.get(Project, uuid.UUID(str(form["project_id"])))
        preset = session.get(DeliveryPreset, uuid.UUID(str(form["preset_id"])))
        if project and preset:
            package = create_package(
                session, project=project, preset=preset, name=str(form.get("name") or f"{project.working_title} -- {preset.name}"),
                output_directory=str(form["output_directory"]), user_id=user.id,
            )
            return RedirectResponse(f"/delivery/packages/{package.id}", status_code=303)
    return RedirectResponse("/delivery", status_code=303)


@router.get("/delivery/packages/{package_id}")
async def package_detail(package_id: str, request: Request, response: Response, session: Session = Depends(get_session), user: User = Depends(require_login), error: str | None = None):
    package = session.get(DeliveryPackage, uuid.UUID(package_id))
    if package is None:
        return RedirectResponse("/delivery", status_code=303)
    preset = session.get(DeliveryPreset, package.preset_id)
    completeness = check_completeness(session, package.project_id, preset)
    csrf_token = get_csrf_token(request)
    return templates.TemplateResponse(
        request, "delivery/detail.html",
        {**base_context(user, "delivery"), "package": package, "preset": preset, "completeness": completeness, "csrf_token": csrf_token, "error": error},
    )


@router.post("/delivery/packages/{package_id}/generate-manifest")
async def generate_manifest_route(package_id: str, request: Request, session: Session = Depends(get_session), user: User = Depends(require_login)):
    package = session.get(DeliveryPackage, uuid.UUID(package_id))
    form = await request.form()
    if package and verify_csrf(request, form.get("csrf_token")):
        generate_manifest(session, package, user_id=user.id)
    return RedirectResponse(f"/delivery/packages/{package_id}", status_code=303)


@router.post("/delivery/packages/{package_id}/approve")
async def approve_package_route(package_id: str, request: Request, session: Session = Depends(get_session), user: User = Depends(require_login)):
    package = session.get(DeliveryPackage, uuid.UUID(package_id))
    form = await request.form()
    if package and verify_csrf(request, form.get("csrf_token")):
        approve_package(session, package, approved_by=user.id)
    return RedirectResponse(f"/delivery/packages/{package_id}", status_code=303)


@router.post("/delivery/packages/{package_id}/execute")
async def execute_package_route(package_id: str, request: Request, session: Session = Depends(get_session), user: User = Depends(require_login)):
    package = session.get(DeliveryPackage, uuid.UUID(package_id))
    form = await request.form()
    if package and verify_csrf(request, form.get("csrf_token")):
        try:
            execute_package(session, package, executed_by=user.id)
        except (FileExistsError, ValueError) as exc:
            from urllib.parse import quote

            return RedirectResponse(f"/delivery/packages/{package_id}?error={quote(str(exc))}", status_code=303)
    return RedirectResponse(f"/delivery/packages/{package_id}", status_code=303)
