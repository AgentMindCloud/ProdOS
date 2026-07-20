"""Analytics: manual CSV import, manual entry, summaries (spec section 16)."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Request, Response
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
    form = await request.form()
    if not verify_csrf(request, form.get("csrf_token")):
        return RedirectResponse("/analytics", status_code=303)

    upload = form.get("csv_file")
    source_name = str(form.get("source_name") or "Manual CSV import")
    period_start = form.get("period_start")
    period_end = form.get("period_end")
    project_id = form.get("project_id") or None

    if upload is not None and hasattr(upload, "read") and period_start and period_end:
        content_bytes = await upload.read()
        content = content_bytes.decode("utf-8", errors="replace")
        parsed = parse_analytics_csv(content)
        source = get_or_create_source(session, source_name, AnalyticsSourceType.OTHER)
        record_import(
            session,
            source=source,
            parsed=parsed,
            reporting_period_start=date.fromisoformat(str(period_start)),
            reporting_period_end=date.fromisoformat(str(period_end)),
            project_id=uuid.UUID(str(project_id)) if project_id else None,
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
