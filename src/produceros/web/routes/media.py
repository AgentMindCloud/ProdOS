"""Authenticated byte-range previews of registered local audio and artwork."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from produceros.models.assets import AssetVersion
from produceros.services.media import preview_file
from produceros.web.deps import get_session, require_login

router = APIRouter(tags=["media"], dependencies=[Depends(require_login)])


@router.get("/asset-versions/{version_id}/preview")
def asset_preview(version_id: uuid.UUID, session: Session = Depends(get_session)) -> FileResponse:
    version = session.get(AssetVersion, version_id)
    preview = preview_file(session, version) if version else None
    if preview is None:
        raise HTTPException(status_code=404, detail="Preview unavailable.")
    return FileResponse(
        preview.path,
        media_type=preview.media_type,
        filename=preview.path.name,
        content_disposition_type="inline",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )
