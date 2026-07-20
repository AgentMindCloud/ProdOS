"""Append-only audit logging, used by every service that changes state or
performs a security-relevant action (spec sections 2, 7, 9, 15, 19)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from produceros.models.system import AuditEvent


def log_event(
    session: Session,
    *,
    event_type: str,
    summary: str,
    user_id: uuid.UUID | None = None,
    device_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        occurred_at=datetime.now(UTC),
        user_id=user_id,
        device_id=device_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary,
        event_metadata=metadata or {},
        ip_address=ip_address,
    )
    session.add(event)
    session.flush()
    return event
