from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from produceros.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from produceros.models.enums import DeadlineType


class Deadline(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "deadlines"

    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"))
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("marketing_campaigns.id"))
    artist_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("artists.id"))
    deadline_type: Mapped[DeadlineType] = mapped_column(
        SAEnum(DeadlineType, native_enum=False, validate_strings=True), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
