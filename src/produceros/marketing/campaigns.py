"""Marketing campaign and content-asset CRUD (spec section 13)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from produceros.models.enums import (
    CampaignStatus,
    CampaignType,
    ContentAssetStatus,
    ContentAssetType,
)
from produceros.models.marketing import ContentAsset, MarketingCampaign
from produceros.services.audit import log_event


def create_campaign(
    session: Session,
    *,
    name: str,
    campaign_type: CampaignType = CampaignType.CUSTOM,
    project_id: uuid.UUID | None = None,
    artist_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    **fields,
) -> MarketingCampaign:
    campaign = MarketingCampaign(
        name=name.strip(),
        campaign_type=campaign_type,
        project_id=project_id,
        artist_id=artist_id,
        status=CampaignStatus.DRAFT,
        **fields,
    )
    session.add(campaign)
    session.flush()
    log_event(
        session,
        event_type="marketing.campaign_created",
        summary=f"Marketing campaign '{campaign.name}' created.",
        user_id=user_id,
        entity_type="MarketingCampaign",
        entity_id=campaign.id,
    )
    return campaign


def list_campaigns(
    session: Session, *, project_id: uuid.UUID | None = None
) -> list[MarketingCampaign]:
    stmt = select(MarketingCampaign)
    if project_id:
        stmt = stmt.where(MarketingCampaign.project_id == project_id)
    return list(session.scalars(stmt.order_by(MarketingCampaign.created_at.desc())))


def create_content_asset(
    session: Session,
    *,
    title: str,
    content_type: ContentAssetType,
    project_id: uuid.UUID | None = None,
    campaign_id: uuid.UUID | None = None,
    **fields,
) -> ContentAsset:
    asset = ContentAsset(
        title=title.strip(),
        content_type=content_type,
        project_id=project_id,
        campaign_id=campaign_id,
        status=ContentAssetStatus.IDEA,
        **fields,
    )
    session.add(asset)
    session.flush()
    return asset


def list_content_assets(
    session: Session, *, project_id: uuid.UUID | None = None, campaign_id: uuid.UUID | None = None
) -> list[ContentAsset]:
    stmt = select(ContentAsset)
    if project_id:
        stmt = stmt.where(ContentAsset.project_id == project_id)
    if campaign_id:
        stmt = stmt.where(ContentAsset.campaign_id == campaign_id)
    return list(session.scalars(stmt.order_by(ContentAsset.created_at.desc())))
