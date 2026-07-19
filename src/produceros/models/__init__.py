"""All ORM models, imported eagerly so ``Base.metadata`` is complete for
Alembic autogeneration and for ``Base.metadata.create_all`` in tests."""

from produceros.db.base import Base
from produceros.models.analytics import AnalyticsImport, AnalyticsMetric, AnalyticsSource
from produceros.models.assets import Asset, AssetVersion, AudioAnalysis
from produceros.models.calendar import Deadline
from produceros.models.catalog import Artist, Project, ProjectTag, ProjectVersion, Tag, Track
from produceros.models.delivery import DeliveryManifestItem, DeliveryPackage, DeliveryPreset
from produceros.models.marketing import ContentAsset, MarketingCampaign, MarketingDraft
from produceros.models.release import ChecklistResult, ChecklistRule, Release
from produceros.models.rights import Clearance, Contributor, RightsShare
from produceros.models.scanner import (
    ApprovedFileOperation,
    ScannerFinding,
    ScannerRoot,
    ScannerRun,
)
from produceros.models.system import AppSetting, AuditEvent, BackupRecord
from produceros.models.user import PairedDevice, User

__all__ = [
    "Base",
    "User",
    "PairedDevice",
    "Artist",
    "Project",
    "Track",
    "ProjectVersion",
    "Tag",
    "ProjectTag",
    "Asset",
    "AssetVersion",
    "AudioAnalysis",
    "Contributor",
    "RightsShare",
    "Clearance",
    "Release",
    "ChecklistRule",
    "ChecklistResult",
    "MarketingCampaign",
    "ContentAsset",
    "MarketingDraft",
    "Deadline",
    "DeliveryPreset",
    "DeliveryPackage",
    "DeliveryManifestItem",
    "AnalyticsSource",
    "AnalyticsImport",
    "AnalyticsMetric",
    "ScannerRoot",
    "ScannerRun",
    "ScannerFinding",
    "ApprovedFileOperation",
    "AuditEvent",
    "AppSetting",
    "BackupRecord",
]
