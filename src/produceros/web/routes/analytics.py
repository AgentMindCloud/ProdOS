"""Analytics: manual CSV import, manual entry, summaries (spec section 16)."""

from __future__ import annotations

import csv
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from produceros.analytics.csv_templates import csv_template_text
from produceros.analytics.importer import parse_analytics_csv
from produceros.analytics.summaries import (
    channel_summary,
    content_performance_ranking,
    cost_summary,
    release_summary,
    revenue_summary,
)
from produceros.models.catalog import Project
from produceros.models.enums import AnalyticsMetricType, AnalyticsSourceType
from produceros.models.user import User
from produceros.services.analytics import add_manual_metric, get_or_create_source, record_import
from produceros.web.app import templates
from produceros.web.context import base_context
from produceros.web.csrf import get_csrf_token, verify_csrf
from produceros.web.deps import get_session, require_login

router = APIRouter(tags=["analytics"], dependencies=[Depends(require_login)])

MAX_CSV_BYTES = 5 * 1024 * 1024
MAX_IMPORT_REQUEST_BYTES = MAX_CSV_BYTES + 64 * 1024


async def _bounded_import_request(request: Request) -> Request:
    """Bound the whole body before multipart can spool an unbounded upload.

    Counting the stream also handles chunked requests and misleading or
    absent Content-Length headers. Only this small CSV endpoint buffers it.
    """
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            declared_size = int(content_length)
        except ValueError as exc:
            raise HTTPException(400, "Invalid Content-Length header.") from exc
        if declared_size > MAX_IMPORT_REQUEST_BYTES:
            raise HTTPException(413, "CSV imports are limited to 5 MiB.")

    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_IMPORT_REQUEST_BYTES:
            raise HTTPException(413, "CSV imports are limited to 5 MiB.")
        body.extend(chunk)

    async def receive():
        return {"type": "http.request", "body": bytes(body), "more_body": False}

    return Request(request.scope, receive=receive)


@router.get("/analytics")
async def analytics_home(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
    user: User = Depends(require_login),
    project_id: str | None = None,
):
    projects = list(session.scalars(select(Project).order_by(Project.working_title)))
    project_uuid = uuid.UUID(project_id) if project_id else None
    summary = release_summary(session, project_uuid) if project_uuid else []
    channels = channel_summary(session, project_id=project_uuid)
    ranking = content_performance_ranking(session, project_id=project_uuid)
    csrf_token = get_csrf_token(request)
    return templates.TemplateResponse(
        request,
        "analytics/index.html",
        {
            **base_context(user, "analytics"),
            "projects": projects,
            "selected_project_id": project_id or "",
            "summary": summary,
            "channels": channels,
            "ranking": ranking,
            "cost_total": cost_summary(session, project_id=project_uuid),
            "revenue_total": revenue_summary(session, project_id=project_uuid),
            "metric_types": list(AnalyticsMetricType),
            "csrf_token": csrf_token,
        },
    )


@router.get("/analytics/csv-template")
async def download_csv_template():
    return PlainTextResponse(
        csv_template_text(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="produceros-analytics-template.csv"'},
    )


@router.post("/analytics/import")
async def import_csv(
    request: Request, session: Session = Depends(get_session), user: User = Depends(require_login)
):
    limited_request = await _bounded_import_request(request)
    async with limited_request.form(max_files=1, max_fields=8, max_part_size=16 * 1024) as form:
        if not verify_csrf(request, form.get("csrf_token")):
            return RedirectResponse("/analytics", status_code=303)

        upload = form.get("csv_file")
        source_name = str(form.get("source_name") or "Manual CSV import")
        period_start = form.get("period_start")
        period_end = form.get("period_end")
        project_id = form.get("project_id") or None

        if upload is not None and hasattr(upload, "read") and period_start and period_end:
            content_bytes = await upload.read(MAX_CSV_BYTES + 1)
            if len(content_bytes) > MAX_CSV_BYTES:
                raise HTTPException(413, "CSV imports are limited to 5 MiB.")
            content = content_bytes.decode("utf-8-sig", errors="replace")
            try:
                parsed = parse_analytics_csv(content)
                start = date.fromisoformat(str(period_start))
                end = date.fromisoformat(str(period_end))
                project_uuid = uuid.UUID(str(project_id)) if project_id else None
            except (ValueError, csv.Error) as exc:
                raise HTTPException(400, f"Could not import CSV: {exc}") from exc
            if end < start:
                raise HTTPException(400, "Period end must be on or after period start.")
            if not parsed.rows:
                raise HTTPException(400, "CSV has no valid data rows. Check the CSV template.")
            if project_uuid and session.get(Project, project_uuid) is None:
                raise HTTPException(400, "Selected project does not exist.")
            source = get_or_create_source(session, source_name, AnalyticsSourceType.OTHER)
            record_import(
                session,
                source=source,
                parsed=parsed,
                reporting_period_start=start,
                reporting_period_end=end,
                project_id=project_uuid,
                original_filename=getattr(upload, "filename", None),
                user_id=user.id,
            )
    return RedirectResponse(
        f"/analytics{'?project_id=' + str(project_id) if project_id else ''}", status_code=303
    )


@router.post("/analytics/manual-entry")
async def manual_entry(
    request: Request, session: Session = Depends(get_session), user: User = Depends(require_login)
):
    form = await request.form()
    if not verify_csrf(request, form.get("csrf_token")):
        return RedirectResponse("/analytics", status_code=303)
    if (
        form.get("metric_type")
        and form.get("value")
        and form.get("period_start")
        and form.get("period_end")
    ):
        source = get_or_create_source(session, "Manual entry", AnalyticsSourceType.OTHER)
        project_id = form.get("project_id") or None
        add_manual_metric(
            session,
            source=source,
            metric_type=AnalyticsMetricType(str(form["metric_type"])),
            value=float(str(form["value"])),
            reporting_period_start=date.fromisoformat(str(form["period_start"])),
            reporting_period_end=date.fromisoformat(str(form["period_end"])),
            project_id=uuid.UUID(str(project_id)) if project_id else None,
            channel=str(form.get("channel") or "") or None,
            user_id=user.id,
        )
    return RedirectResponse("/analytics", status_code=303)
