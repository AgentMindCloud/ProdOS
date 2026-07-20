"""Backup, restore, and data export (spec section 20)."""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from produceros.config import get_settings
from produceros.models.enums import BackupType
from produceros.models.system import BackupRecord
from produceros.models.user import User
from produceros.services.backup import (
    create_backup,
    export_audio_manifest,
    export_metadata_json,
    list_backups,
    restore_backup,
    restore_dry_run,
    verify_backup,
)
from produceros.web.app import templates
from produceros.web.context import base_context
from produceros.web.csrf import get_csrf_token, verify_csrf
from produceros.web.deps import get_session, require_login

router = APIRouter(tags=["backup"], dependencies=[Depends(require_login)])


@router.get("/backup")
async def backup_home(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    backups = list_backups(session)
    csrf_token = get_csrf_token(request)
    return templates.TemplateResponse(
        request,
        "backup/index.html",
        {**base_context(user, "settings"), "backups": backups, "csrf_token": csrf_token},
    )


@router.post("/backup/create")
async def create_backup_route(
    request: Request, session: Session = Depends(get_session), user: User = Depends(require_login)
):
    form = await request.form()
    if verify_csrf(request, form.get("csrf_token")):
        settings = get_settings()
        create_backup(session, settings, backup_type=BackupType.MANUAL, user_id=user.id)
    return RedirectResponse("/backup", status_code=303)


@router.post("/backup/{backup_id}/verify")
async def verify_backup_route(
    backup_id: str,
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    record = session.get(BackupRecord, uuid.UUID(backup_id))
    form = await request.form()
    if record and verify_csrf(request, form.get("csrf_token")):
        verify_backup(session, record, user_id=user.id)
    return RedirectResponse("/backup", status_code=303)


@router.post("/backup/{backup_id}/restore-dry-run")
async def restore_dry_run_route(
    backup_id: str,
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    record = session.get(BackupRecord, uuid.UUID(backup_id))
    if record is None:
        return RedirectResponse("/backup", status_code=303)
    result = restore_dry_run(record.file_path)
    return JSONResponse(
        {
            "ok": result.ok,
            "integrity_check": result.integrity_check,
            "table_counts": result.table_counts,
            "warnings": result.warnings,
        }
    )


@router.post("/backup/{backup_id}/restore-confirm")
async def restore_confirm_route(
    backup_id: str,
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
):
    record = session.get(BackupRecord, uuid.UUID(backup_id))
    form = await request.form()
    if record and verify_csrf(request, form.get("csrf_token")) and form.get("confirm") == "yes":
        settings = get_settings()
        restore_backup(settings, record.file_path, confirmed=True)
    return RedirectResponse("/backup", status_code=303)


@router.get("/backup/export/metadata.json")
async def export_metadata(
    session: Session = Depends(get_session), user: User = Depends(require_login)
):
    data = export_metadata_json(session)
    return Response(
        content=json.dumps(data, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="produceros-metadata-export.json"'},
    )


@router.get("/backup/export/audio-manifest.json")
async def export_audio_manifest_route(
    session: Session = Depends(get_session), user: User = Depends(require_login)
):
    data = export_audio_manifest(session)
    return Response(
        content=json.dumps(data, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="produceros-audio-manifest.json"'},
    )
