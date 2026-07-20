"""Artists, projects, tracks, contributors, rights, clearances, and asset
registration (spec sections 6-11)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from produceros.models.assets import Asset, AssetVersion
from produceros.models.catalog import Artist, Project
from produceros.models.enums import (
    DEFAULT_PROJECT_STATES,
    AssetType,
    ClearanceStatus,
    ClearanceType,
    ContributorRole,
    ExplicitStatus,
    ProjectState,
    ProRegistrationStatus,
    RightsShareType,
)
from produceros.models.rights import Clearance, Contributor, RightsShare
from produceros.models.user import User
from produceros.services import assets as asset_service
from produceros.services import catalog as catalog_service
from produceros.services import rights as rights_service
from produceros.services.audit import log_event
from produceros.web.app import templates
from produceros.web.context import base_context
from produceros.web.csrf import get_csrf_token, verify_csrf
from produceros.web.deps import get_session, require_login

router = APIRouter(tags=["catalog"], dependencies=[Depends(require_login)])


def _get_project_or_404(session: Session, project_id: str) -> Project:
    project = session.get(Project, uuid.UUID(project_id))
    if project is None:
        raise LookupError("Project not found")
    return project


# ---------------------------------------------------------------- Artists
@router.get("/artists")
async def list_artists(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    artists = list(session.scalars(select(Artist).order_by(Artist.name)))
    csrf_token = get_csrf_token(request)
    return templates.TemplateResponse(
        request,
        "catalog/artists_list.html",
        {**base_context(user, "projects"), "artists": artists, "csrf_token": csrf_token},
    )


@router.post("/artists/new")
async def create_artist(
    request: Request, session: Session = Depends(get_session), user: User = Depends(require_login)
):
    form = await request.form()
    if verify_csrf(request, form.get("csrf_token")):
        name = str(form.get("name", "")).strip()
        if name:
            catalog_service.create_artist(session, name=name, user_id=user.id)
    return RedirectResponse("/artists", status_code=303)


# ---------------------------------------------------------------- Projects
@router.get("/projects")
async def list_projects(
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
    search: str | None = None,
    state: str | None = None,
    artist_id: str | None = None,
):
    state_enum = ProjectState(state) if state else None
    artist_uuid = uuid.UUID(artist_id) if artist_id else None
    projects = catalog_service.list_projects(
        session, artist_id=artist_uuid, state=state_enum, search=search
    )
    artists = list(session.scalars(select(Artist).order_by(Artist.name)))
    return templates.TemplateResponse(
        request,
        "catalog/projects_list.html",
        {
            **base_context(user, "projects"),
            "projects": projects,
            "artists": artists,
            "states": list(DEFAULT_PROJECT_STATES),
            "filters": {"search": search or "", "state": state or "", "artist_id": artist_id or ""},
        },
    )


@router.get("/projects/new")
async def new_project_form(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    artists = list(session.scalars(select(Artist).order_by(Artist.name)))
    csrf_token = get_csrf_token(request)
    return templates.TemplateResponse(
        request,
        "catalog/project_form.html",
        {
            **base_context(user, "projects"),
            "artists": artists,
            "csrf_token": csrf_token,
            "project": None,
        },
    )


@router.post("/projects/new")
async def create_project(
    request: Request, session: Session = Depends(get_session), user: User = Depends(require_login)
):
    form = await request.form()
    if not verify_csrf(request, form.get("csrf_token")):
        return RedirectResponse("/projects/new", status_code=303)

    working_title = str(form.get("working_title", "")).strip()
    if not working_title:
        return RedirectResponse("/projects/new", status_code=303)

    artist_id = str(form.get("artist_id") or "") or None
    project = catalog_service.create_project(
        session,
        working_title=working_title,
        artist_id=uuid.UUID(artist_id) if artist_id else None,
        user_id=user.id,
        genre=str(form.get("genre") or "") or None,
        bpm=float(str(form["bpm"])) if form.get("bpm") else None,
        musical_key=str(form.get("musical_key") or "") or None,
    )
    return RedirectResponse(f"/projects/{project.id}", status_code=303)


@router.get("/projects/{project_id}")
async def project_detail(
    project_id: str,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    project = _get_project_or_404(session, project_id)
    artists = list(session.scalars(select(Artist).order_by(Artist.name)))
    contributors = list(
        session.scalars(select(Contributor).where(Contributor.project_id == project.id))
    )
    rights_shares = list(
        session.scalars(select(RightsShare).where(RightsShare.project_id == project.id))
    )
    clearances = list(session.scalars(select(Clearance).where(Clearance.project_id == project.id)))
    validations = rights_service.validate_rights_shares(session, project.id)
    assets = list(session.scalars(select(Asset).where(Asset.project_id == project.id)))
    asset_versions = {
        a.id: list(
            session.scalars(
                select(AssetVersion)
                .where(AssetVersion.asset_id == a.id)
                .order_by(AssetVersion.version_number.desc())
            )
        )
        for a in assets
    }
    csrf_token = get_csrf_token(request)

    return templates.TemplateResponse(
        request,
        "catalog/project_detail.html",
        {
            **base_context(user, "projects"),
            "project": project,
            "artists": artists,
            "contributors": contributors,
            "rights_shares": rights_shares,
            "clearances": clearances,
            "validations": validations,
            "assets": assets,
            "asset_versions": asset_versions,
            "asset_types": list(AssetType),
            "contributor_roles": list(ContributorRole),
            "share_types": list(RightsShareType),
            "clearance_types": list(ClearanceType),
            "clearance_statuses": list(ClearanceStatus),
            "explicit_statuses": list(ExplicitStatus),
            "pro_statuses": list(ProRegistrationStatus),
            "states": list(DEFAULT_PROJECT_STATES),
            "csrf_token": csrf_token,
        },
    )


@router.post("/projects/{project_id}/edit")
async def edit_project(
    project_id: str,
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    project = _get_project_or_404(session, project_id)
    form = await request.form()
    if not verify_csrf(request, form.get("csrf_token")):
        return RedirectResponse(f"/projects/{project_id}", status_code=303)

    fields: dict = {}
    text_fields = [
        "working_title",
        "final_title",
        "producer_name",
        "description",
        "musical_key",
        "time_signature",
        "genre",
        "subgenre",
        "mood",
        "language",
        "vocal_style",
        "notes",
        "fl_project_path",
        "fl_project_zip_path",
        "project_root_path",
        "revision_notes",
        "master_owner",
        "composition_owner",
        "distributor",
        "isrc",
        "upc",
        "release_description",
    ]
    for key in text_fields:
        if key in form:
            fields[key] = str(form.get(key) or "") or None

    if "bpm" in form:
        fields["bpm"] = float(str(form["bpm"])) if form.get("bpm") else None
    if "energy" in form:
        fields["energy"] = int(str(form["energy"])) if form.get("energy") else None
    if "artist_id" in form:
        fields["artist_id"] = uuid.UUID(str(form["artist_id"])) if form.get("artist_id") else None
    if "explicit_status" in form and form.get("explicit_status"):
        fields["explicit_status"] = ExplicitStatus(str(form["explicit_status"]))
    if "pro_registration_status" in form and form.get("pro_registration_status"):
        fields["pro_registration_status"] = ProRegistrationStatus(
            str(form["pro_registration_status"])
        )
    if "sample_clearance_status" in form and form.get("sample_clearance_status"):
        fields["sample_clearance_status"] = ClearanceStatus(str(form["sample_clearance_status"]))
    if "one_stop_clearance_status" in form and form.get("one_stop_clearance_status"):
        fields["one_stop_clearance_status"] = ClearanceStatus(
            str(form["one_stop_clearance_status"])
        )
    if "split_confirmed" in form:
        fields["split_confirmed"] = form.get("split_confirmed") == "on"
    for list_field in ("featured_artists", "alternate_titles", "instruments", "similar_artists"):
        if list_field in form:
            raw = str(form.get(list_field) or "")
            fields[list_field] = [v.strip() for v in raw.split(",") if v.strip()]
    if "tags" in form:
        catalog_service.set_project_tags(
            session,
            project,
            [t.strip() for t in str(form.get("tags") or "").split(",") if t.strip()],
        )

    catalog_service.update_project(session, project, user_id=user.id, **fields)
    return RedirectResponse(f"/projects/{project_id}", status_code=303)


@router.post("/projects/{project_id}/state")
async def change_state(
    project_id: str,
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    project = _get_project_or_404(session, project_id)
    form = await request.form()
    if verify_csrf(request, form.get("csrf_token")) and form.get("state"):
        catalog_service.change_project_state(
            session,
            project,
            ProjectState(str(form["state"])),
            user_id=user.id,
            note=str(form.get("note") or "") or None,
        )
    return RedirectResponse(f"/projects/{project_id}", status_code=303)


@router.post("/projects/{project_id}/tracks/new")
async def add_track(
    project_id: str,
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    project = _get_project_or_404(session, project_id)
    form = await request.form()
    if verify_csrf(request, form.get("csrf_token")) and form.get("title"):
        catalog_service.create_track(session, project, title=str(form["title"]))
    return RedirectResponse(f"/projects/{project_id}", status_code=303)


# ------------------------------------------------------------ Rights & clearances
@router.post("/projects/{project_id}/contributors/new")
async def add_contributor(
    project_id: str,
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    project = _get_project_or_404(session, project_id)
    form = await request.form()
    if verify_csrf(request, form.get("csrf_token")) and form.get("name") and form.get("role"):
        rights_service.add_contributor(
            session,
            project.id,
            name=str(form["name"]),
            role=ContributorRole(str(form["role"])),
            email=str(form.get("email") or "") or None,
            pro_affiliation=str(form.get("pro_affiliation") or "") or None,
        )
    return RedirectResponse(f"/projects/{project_id}#rights", status_code=303)


@router.post("/projects/{project_id}/contributors/{contributor_id}/approve")
async def approve_contributor(
    project_id: str,
    contributor_id: str,
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    form = await request.form()
    contributor = session.get(Contributor, uuid.UUID(contributor_id))
    if contributor and verify_csrf(request, form.get("csrf_token")):
        contributor.approved = True
        session.flush()
        log_event(
            session,
            event_type="rights.contributor_approved",
            summary=f"Contributor '{contributor.name}' approved.",
            user_id=user.id,
            entity_type="Contributor",
            entity_id=contributor.id,
        )
    return RedirectResponse(f"/projects/{project_id}#rights", status_code=303)


@router.post("/projects/{project_id}/rights-shares/new")
async def add_rights_share(
    project_id: str,
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    project = _get_project_or_404(session, project_id)
    form = await request.form()
    if (
        verify_csrf(request, form.get("csrf_token"))
        and form.get("holder_name")
        and form.get("share_type")
        and form.get("percentage")
    ):
        rights_service.add_rights_share(
            session,
            project.id,
            user_id=user.id,
            holder_name=str(form["holder_name"]),
            share_type=RightsShareType(str(form["share_type"])),
            percentage=float(str(form["percentage"])),
            confirmed=form.get("confirmed") == "on",
        )
    return RedirectResponse(f"/projects/{project_id}#rights", status_code=303)


@router.post("/rights-shares/{share_id}/update")
async def update_rights_share(
    share_id: str,
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    share = session.get(RightsShare, uuid.UUID(share_id))
    form = await request.form()
    if share and verify_csrf(request, form.get("csrf_token")) and form.get("percentage"):
        rights_service.update_rights_share_percentage(
            session, share, float(str(form["percentage"])), user_id=user.id
        )
        share.confirmed = form.get("confirmed") == "on"
        session.flush()
    return RedirectResponse(
        f"/projects/{share.project_id}#rights" if share else "/projects", status_code=303
    )


@router.post("/projects/{project_id}/clearances/new")
async def add_clearance(
    project_id: str,
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    project = _get_project_or_404(session, project_id)
    form = await request.form()
    if (
        verify_csrf(request, form.get("csrf_token"))
        and form.get("description")
        and form.get("clearance_type")
    ):
        rights_service.add_clearance(
            session,
            project.id,
            clearance_type=ClearanceType(str(form["clearance_type"])),
            description=str(form["description"]),
            rights_holder_contact=str(form.get("rights_holder_contact") or "") or None,
        )
    return RedirectResponse(f"/projects/{project_id}#rights", status_code=303)


@router.post("/clearances/{clearance_id}/resolve")
async def resolve_clearance(
    clearance_id: str,
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    clearance = session.get(Clearance, uuid.UUID(clearance_id))
    form = await request.form()
    if clearance and verify_csrf(request, form.get("csrf_token")) and form.get("status"):
        rights_service.resolve_clearance(
            session, clearance, ClearanceStatus(str(form["status"])), user_id=user.id
        )
    return RedirectResponse(
        f"/projects/{clearance.project_id}#rights" if clearance else "/projects", status_code=303
    )


# --------------------------------------------------------------- Asset registration
@router.post("/projects/{project_id}/assets/register")
async def register_asset(
    project_id: str,
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    project = _get_project_or_404(session, project_id)
    form = await request.form()
    if (
        verify_csrf(request, form.get("csrf_token"))
        and form.get("asset_type")
        and form.get("file_path")
    ):
        asset_service.register_asset_version(
            session,
            project=project,
            asset_type=AssetType(str(form["asset_type"])),
            file_path=str(form["file_path"]),
            mark_current=form.get("mark_current") == "on",
            user_id=user.id,
        )
    return RedirectResponse(f"/projects/{project_id}#assets", status_code=303)


@router.post("/asset-versions/{version_id}/set-current")
async def set_current_version(
    version_id: str,
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    version = session.get(AssetVersion, uuid.UUID(version_id))
    form = await request.form()
    if version and verify_csrf(request, form.get("csrf_token")):
        asset = session.get(Asset, version.asset_id)
        if asset is not None:
            asset_service.set_current_version(session, asset, version, user_id=user.id)
            return RedirectResponse(f"/projects/{asset.project_id}#assets", status_code=303)
    return RedirectResponse("/projects", status_code=303)
