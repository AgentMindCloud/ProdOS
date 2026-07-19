"""Contributors, rights shares, and clearances (spec section 6, 12).

Percentages are only ever changed by an explicit call from a route acting
on a user's form submission -- there is no automatic rebalancing anywhere
in this module. ``validate_rights_shares`` only ever reports; it never
mutates.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from produceros.models.enums import ClearanceStatus, RightsShareType
from produceros.models.rights import Clearance, Contributor, RightsShare
from produceros.services.audit import log_event

PERCENTAGE_TOLERANCE = 0.01


@dataclass
class RightsShareValidation:
    share_type: RightsShareType
    total_percentage: float
    is_exactly_100: bool
    all_confirmed: bool
    warning: str | None


def add_contributor(session: Session, project_id: uuid.UUID, **fields) -> Contributor:
    contributor = Contributor(project_id=project_id, **fields)
    session.add(contributor)
    session.flush()
    return contributor


def add_rights_share(
    session: Session, project_id: uuid.UUID, *, user_id: uuid.UUID | None = None, **fields
) -> RightsShare:
    share = RightsShare(project_id=project_id, **fields)
    session.add(share)
    session.flush()
    log_event(
        session,
        event_type="rights.share_added",
        summary=f"Added {share.share_type.value} share for '{share.holder_name}': {share.percentage}%.",
        user_id=user_id,
        entity_type="RightsShare",
        entity_id=share.id,
    )
    return share


def update_rights_share_percentage(
    session: Session, share: RightsShare, new_percentage: float, *, user_id: uuid.UUID | None = None
) -> RightsShare:
    """The only way a percentage changes: an explicit, audited edit."""
    old = share.percentage
    share.percentage = new_percentage
    session.flush()
    log_event(
        session,
        event_type="rights.share_percentage_changed",
        summary=f"'{share.holder_name}' {share.share_type.value} share changed from {old}% to {new_percentage}% (explicit edit).",
        user_id=user_id,
        entity_type="RightsShare",
        entity_id=share.id,
    )
    return share


def validate_rights_shares(session: Session, project_id: uuid.UUID) -> list[RightsShareValidation]:
    results = []
    for share_type in RightsShareType:
        shares = list(
            session.scalars(
                select(RightsShare).where(
                    RightsShare.project_id == project_id, RightsShare.share_type == share_type
                )
            )
        )
        if not shares:
            continue
        total = round(sum(float(s.percentage) for s in shares), 3)
        is_100 = abs(total - 100.0) <= PERCENTAGE_TOLERANCE
        all_confirmed = all(s.confirmed for s in shares)
        warning = None
        if not is_100:
            warning = f"{share_type.value.title()} shares total {total}%, not 100%."
        elif not all_confirmed:
            warning = f"{share_type.value.title()} shares total 100% but are not all confirmed."
        results.append(
            RightsShareValidation(
                share_type=share_type,
                total_percentage=total,
                is_exactly_100=is_100,
                all_confirmed=all_confirmed,
                warning=warning,
            )
        )
    return results


def add_clearance(session: Session, project_id: uuid.UUID, **fields) -> Clearance:
    clearance = Clearance(project_id=project_id, status=ClearanceStatus.UNRESOLVED, **fields)
    session.add(clearance)
    session.flush()
    return clearance


def resolve_clearance(
    session: Session, clearance: Clearance, status: ClearanceStatus, *, user_id: uuid.UUID | None = None
) -> Clearance:
    from datetime import datetime, timezone

    clearance.status = status
    clearance.resolved_at = datetime.now(timezone.utc)
    session.flush()
    log_event(
        session,
        event_type="rights.clearance_resolved",
        summary=f"Clearance '{clearance.description[:60]}' marked {status.value}.",
        user_id=user_id,
        entity_type="Clearance",
        entity_id=clearance.id,
    )
    return clearance
