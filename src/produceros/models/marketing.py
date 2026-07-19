from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from produceros.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from produceros.models.enums import (
    CampaignStatus,
    CampaignType,
    ContentAssetStatus,
    ContentAssetType,
    DraftStatus,
    MarketingDraftType,
)


class MarketingCampaign(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "marketing_campaigns"

    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"))
    artist_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("artists.id"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    campaign_type: Mapped[CampaignType] = mapped_column(
        SAEnum(CampaignType, native_enum=False, validate_strings=True),
        default=CampaignType.CUSTOM,
        nullable=False,
    )
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[CampaignStatus] = mapped_column(
        SAEnum(CampaignStatus, native_enum=False, validate_strings=True),
        default=CampaignStatus.DRAFT,
        nullable=False,
    )
    goal: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)


class ContentAsset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A tracked marketing content idea/piece (not an audio Asset)."""

    __tablename__ = "content_assets"

    campaign_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("marketing_campaigns.id"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"))
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content_type: Mapped[ContentAssetType] = mapped_column(
        SAEnum(ContentAssetType, native_enum=False, validate_strings=True), nullable=False
    )
    status: Mapped[ContentAssetStatus] = mapped_column(
        SAEnum(ContentAssetStatus, native_enum=False, validate_strings=True),
        default=ContentAssetStatus.IDEA,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    file_path: Mapped[str | None] = mapped_column(String(1024))


class MarketingDraft(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A locally generated, editable text draft. Never sent or published
    automatically; see produceros.marketing for the template engine."""

    __tablename__ = "marketing_drafts"

    campaign_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("marketing_campaigns.id"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"))
    draft_type: Mapped[MarketingDraftType] = mapped_column(
        SAEnum(MarketingDraftType, native_enum=False, validate_strings=True), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[DraftStatus] = mapped_column(
        SAEnum(DraftStatus, native_enum=False, validate_strings=True),
        default=DraftStatus.DRAFT,
        nullable=False,
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    template_version: Mapped[str] = mapped_column(String(20), default="1", nullable=False)
