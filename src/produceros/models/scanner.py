from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from produceros.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from produceros.models.enums import (
    FileOperationStatus,
    FileOperationType,
    FindingStatus,
    FindingType,
    ScannerRunStatus,
    ScannerTrigger,
)


class ScannerRoot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "scanner_roots"

    path: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    label: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ScannerRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "scanner_runs"

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[ScannerRunStatus] = mapped_column(
        SAEnum(ScannerRunStatus, native_enum=False, validate_strings=True),
        default=ScannerRunStatus.RUNNING,
        nullable=False,
    )
    scanned_roots: Mapped[list] = mapped_column(JSON, default=list)
    files_scanned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    findings_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    triggered_by: Mapped[ScannerTrigger] = mapped_column(
        SAEnum(ScannerTrigger, native_enum=False, validate_strings=True),
        default=ScannerTrigger.MANUAL,
        nullable=False,
    )
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ScannerFinding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "scanner_findings"

    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scanner_runs.id"), nullable=False)
    finding_type: Mapped[FindingType] = mapped_column(
        SAEnum(FindingType, native_enum=False, validate_strings=True), nullable=False
    )
    path: Mapped[str] = mapped_column(String(2048), nullable=False)
    related_asset_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("asset_versions.id")
    )
    duplicate_of_path: Mapped[str | None] = mapped_column(String(2048))
    content_hash: Mapped[str | None] = mapped_column(String(64))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    detail: Mapped[str | None] = mapped_column(Text)
    status: Mapped[FindingStatus] = mapped_column(
        SAEnum(FindingStatus, native_enum=False, validate_strings=True),
        default=FindingStatus.NEW,
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class ApprovedFileOperation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A user-approved, audited file operation. ProducerOS never performs
    rename/move/delete/copy/replace on disk without a row here first
    transitioning to ``approved``, and dry-run defaults to True."""

    __tablename__ = "approved_file_operations"

    finding_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("scanner_findings.id"))
    operation_type: Mapped[FileOperationType] = mapped_column(
        SAEnum(FileOperationType, native_enum=False, validate_strings=True), nullable=False
    )
    source_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    destination_path: Mapped[str | None] = mapped_column(String(2048))
    status: Mapped[FileOperationStatus] = mapped_column(
        SAEnum(FileOperationStatus, native_enum=False, validate_strings=True),
        default=FileOperationStatus.PENDING_APPROVAL,
        nullable=False,
    )
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result_detail: Mapped[str | None] = mapped_column(Text)
