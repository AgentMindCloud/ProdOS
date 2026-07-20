"""Deadlines, calendar views, and .ics export (spec section 14).

No external calendar API is used; .ics generation is a small local
implementation of RFC 5545 covering the fields ProducerOS needs.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from produceros.models.calendar import Deadline
from produceros.models.enums import DeadlineType
from produceros.services.audit import log_event

ICS_DATE_FMT = "%Y%m%d"
ICS_DATETIME_FMT = "%Y%m%dT%H%M%SZ"


def create_deadline(
    session: Session,
    *,
    title: str,
    deadline_type: DeadlineType,
    due_date: date,
    project_id: uuid.UUID | None = None,
    campaign_id: uuid.UUID | None = None,
    artist_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    notes: str | None = None,
) -> Deadline:
    deadline = Deadline(
        title=title.strip(),
        deadline_type=deadline_type,
        due_date=due_date,
        project_id=project_id,
        campaign_id=campaign_id,
        artist_id=artist_id,
        notes=notes,
    )
    session.add(deadline)
    session.flush()
    log_event(
        session,
        event_type="deadline.created",
        summary=f"Deadline '{deadline.title}' created for {due_date.isoformat()}.",
        user_id=user_id,
        entity_type="Deadline",
        entity_id=deadline.id,
    )
    return deadline


def complete_deadline(
    session: Session, deadline: Deadline, *, user_id: uuid.UUID | None = None
) -> Deadline:
    deadline.completed_at = datetime.now(UTC)
    session.flush()
    log_event(
        session,
        event_type="deadline.completed",
        summary=f"Deadline '{deadline.title}' marked done.",
        user_id=user_id,
        entity_type="Deadline",
        entity_id=deadline.id,
    )
    return deadline


def list_deadlines(
    session: Session,
    *,
    project_id: uuid.UUID | None = None,
    artist_id: uuid.UUID | None = None,
    campaign_id: uuid.UUID | None = None,
    deadline_type: DeadlineType | None = None,
    start: date | None = None,
    end: date | None = None,
    include_done: bool = True,
) -> list[Deadline]:
    stmt = select(Deadline)
    if project_id:
        stmt = stmt.where(Deadline.project_id == project_id)
    if artist_id:
        stmt = stmt.where(Deadline.artist_id == artist_id)
    if campaign_id:
        stmt = stmt.where(Deadline.campaign_id == campaign_id)
    if deadline_type:
        stmt = stmt.where(Deadline.deadline_type == deadline_type)
    if start:
        stmt = stmt.where(Deadline.due_date >= start)
    if end:
        stmt = stmt.where(Deadline.due_date <= end)
    if not include_done:
        stmt = stmt.where(Deadline.completed_at.is_(None), Deadline.cancelled_at.is_(None))
    return list(session.scalars(stmt.order_by(Deadline.due_date)))


def upcoming(session: Session, *, days: int = 30, **filters) -> list[Deadline]:
    today = date.today()
    return list_deadlines(
        session, start=today, end=today + timedelta(days=days), include_done=False, **filters
    )


def overdue(session: Session, **filters) -> list[Deadline]:
    today = date.today()
    deadlines = list_deadlines(
        session, end=today - timedelta(days=1), include_done=False, **filters
    )
    return deadlines


def _escape_ics_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def export_ics(deadlines: list[Deadline]) -> str:
    """Render deadlines as a minimal, valid RFC 5545 .ics calendar."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ProducerOS//Release Calendar//EN",
        "CALSCALE:GREGORIAN",
    ]
    now_stamp = datetime.now(UTC).strftime(ICS_DATETIME_FMT)
    for deadline in deadlines:
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{deadline.id}@produceros.local",
                f"DTSTAMP:{now_stamp}",
                f"DTSTART;VALUE=DATE:{deadline.due_date.strftime(ICS_DATE_FMT)}",
                f"SUMMARY:{_escape_ics_text(deadline.title)}",
                f"CATEGORIES:{deadline.deadline_type.value}",
            ]
        )
        if deadline.notes:
            lines.append(f"DESCRIPTION:{_escape_ics_text(deadline.notes)}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
