"""All enumerations used by the data model.

Values are persisted as plain strings (``native_enum=False`` wherever used
in a column) so SQLite and PostgreSQL behave identically and adding a new
value never requires an ``ALTER TYPE`` migration.
"""

from __future__ import annotations

from enum import StrEnum


class ProjectState(StrEnum):
    IDEA = "IDEA"
    ARRANGEMENT = "ARRANGEMENT"
    PRODUCTION = "PRODUCTION"
    VOCALS = "VOCALS"
    EDITING = "EDITING"
    MIX = "MIX"
    MASTER = "MASTER"
    RELEASE_READY = "RELEASE_READY"
    SCHEDULED = "SCHEDULED"
    RELEASED = "RELEASED"
    ON_HOLD = "ON_HOLD"
    ARCHIVED = "ARCHIVED"


DEFAULT_PROJECT_STATES: tuple[str, ...] = tuple(s.value for s in ProjectState)


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AssetType(StrEnum):
    FL_PROJECT = "fl_project"
    FL_PROJECT_ZIP = "fl_project_zip"
    MIX = "mix"
    MASTER = "master"
    INSTRUMENTAL = "instrumental"
    ACAPELLA = "acapella"
    CLEAN_VERSION = "clean_version"
    NO_DRUMS = "no_drums_version"
    NO_VOCALS = "no_vocals_version"
    STEMS = "stems"
    ARTWORK = "artwork"
    LYRICS = "lyrics"
    DOCUMENT = "document"
    VIDEO = "video"
    OTHER = "other"


class MetadataConfidence(StrEnum):
    USER_CONFIRMED = "user_confirmed"
    EMBEDDED = "embedded"
    MEASURED = "measured"
    ESTIMATED = "estimated"


class ReleaseType(StrEnum):
    STREAMING_SINGLE = "streaming_single"
    EP = "ep"
    ALBUM = "album"
    INSTRUMENTAL = "instrumental"
    REMIX = "remix"
    CLIENT_DELIVERY = "client_delivery"
    BEAT_LICENSE = "beat_license"
    SYNC_PITCH = "sync_pitch"
    SOCIAL_ONLY = "social_only"


class ExplicitStatus(StrEnum):
    NOT_SET = "not_set"
    EXPLICIT = "explicit"
    CLEAN = "clean"


class ClearanceType(StrEnum):
    SAMPLE = "sample"
    ONE_STOP = "one_stop"
    INTERPOLATION = "interpolation"
    OTHER = "other"


class ClearanceStatus(StrEnum):
    UNRESOLVED = "unresolved"
    CLEARED = "cleared"
    DENIED = "denied"
    NOT_APPLICABLE = "not_applicable"


class ProRegistrationStatus(StrEnum):
    NOT_REGISTERED = "not_registered"
    PENDING = "pending"
    REGISTERED = "registered"
    NOT_APPLICABLE = "not_applicable"


class ContributorRole(StrEnum):
    WRITER = "writer"
    PRODUCER = "producer"
    PERFORMER = "performer"
    PUBLISHER = "publisher"
    ENGINEER = "engineer"
    FEATURED_ARTIST = "featured_artist"
    OTHER = "other"


class RightsShareType(StrEnum):
    MASTER = "master"
    COMPOSITION = "composition"


class ChecklistCategory(StrEnum):
    AUDIO = "audio"
    METADATA = "metadata"
    RIGHTS = "rights"
    MARKETING = "marketing"


class ChecklistSeverity(StrEnum):
    BLOCKING = "blocking"
    RECOMMENDED = "recommended"
    WARNING = "warning"


class ChecklistStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    WAIVED = "waived"
    BLOCKING = "blocking"


class ReleaseStatus(StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RELEASED = "released"


class MarketingDraftType(StrEnum):
    RELEASE_ANNOUNCEMENT = "release_announcement"
    INSTAGRAM_CAPTION = "instagram_caption"
    TIKTOK_CAPTION = "tiktok_caption"
    YOUTUBE_DESCRIPTION = "youtube_description"
    SHORT_VIDEO_HOOK = "short_video_hook"
    BEHIND_THE_SCENES = "behind_the_scenes"
    PRODUCTION_BREAKDOWN = "production_breakdown"
    EMAIL_ANNOUNCEMENT = "email_announcement"
    CREATOR_OUTREACH = "creator_outreach"
    DJ_OUTREACH = "dj_outreach"
    PLAYLIST_OUTREACH = "playlist_outreach"
    SYNC_PITCH = "sync_pitch"
    PRESS_RELEASE_OUTLINE = "press_release_outline"
    FOUR_WEEK_CAMPAIGN = "four_week_campaign"
    SIX_WEEK_CAMPAIGN = "six_week_campaign"
    POST_RELEASE_CAMPAIGN = "post_release_campaign"


class DraftStatus(StrEnum):
    DRAFT = "draft"
    EDITED = "edited"
    ARCHIVED = "archived"


class CampaignType(StrEnum):
    FOUR_WEEK = "four_week"
    SIX_WEEK = "six_week"
    POST_RELEASE = "post_release"
    CUSTOM = "custom"


class CampaignStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ContentAssetType(StrEnum):
    SHORT_VIDEO = "short_video"
    IMAGE = "image"
    CAROUSEL = "carousel"
    STORY = "story"
    OTHER = "other"


class ContentAssetStatus(StrEnum):
    IDEA = "idea"
    DRAFTED = "drafted"
    READY = "ready"
    ARCHIVED = "archived"


class DeadlineType(StrEnum):
    ARRANGEMENT_COMPLETE = "arrangement_complete"
    RECORDING = "recording"
    MIX_DELIVERY = "mix_delivery"
    MIX_APPROVAL = "mix_approval"
    MASTER_DELIVERY = "master_delivery"
    MASTER_APPROVAL = "master_approval"
    ARTWORK = "artwork"
    DISTRIBUTOR_SUBMISSION = "distributor_submission"
    PLAYLIST_PITCH = "playlist_pitch"
    CONTENT_CREATION = "content_creation"
    RELEASE = "release"
    POST_RELEASE_CONTENT = "post_release_content"
    REMIX = "remix"
    CLIENT_DELIVERY = "client_delivery"


class DeadlineStatus(StrEnum):
    UPCOMING = "upcoming"
    OVERDUE = "overdue"
    DONE = "done"
    CANCELLED = "cancelled"


class DeliveryPresetType(StrEnum):
    CLIENT = "client"
    SYNC = "sync"
    DISTRIBUTOR = "distributor"


class DeliveryPackageStatus(StrEnum):
    DRAFT = "draft"
    DRY_RUN = "dry_run"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalyticsSourceType(StrEnum):
    STREAMING = "streaming"
    SOCIAL = "social"
    EMAIL = "email"
    ADVERTISING = "advertising"
    SALES = "sales"
    OTHER = "other"


class RawOrCalculated(StrEnum):
    RAW = "raw"
    CALCULATED = "calculated"


class AnalyticsMetricType(StrEnum):
    STREAMS = "streams"
    LISTENERS = "listeners"
    SAVES = "saves"
    FOLLOWERS = "followers"
    PLAYLIST_ADDITIONS = "playlist_additions"
    VIDEO_VIEWS = "video_views"
    WATCH_TIME = "watch_time"
    LIKES = "likes"
    SHARES = "shares"
    COMMENTS = "comments"
    LINK_CLICKS = "link_clicks"
    EMAIL_SIGNUPS = "email_signups"
    ADVERTISING_SPEND = "advertising_spend"
    REVENUE = "revenue"
    BEAT_SALES = "beat_sales"
    LICENSING_REVENUE = "licensing_revenue"
    SYNC_INQUIRIES = "sync_inquiries"


class FindingType(StrEnum):
    NEW_FILE = "new_file"
    CHANGED_FILE = "changed_file"
    MISSING_FILE = "missing_file"
    EXACT_DUPLICATE = "exact_duplicate"
    POSSIBLE_DUPLICATE = "possible_duplicate"
    NEW_PROJECT_VERSION = "new_project_version"
    NEW_MIX_VERSION = "new_mix_version"
    NEW_MASTER_VERSION = "new_master_version"
    UNEXPECTED_FILE = "unexpected_file"
    INVALID_PATH = "invalid_path"
    OUTSIDE_ROOT = "outside_root"
    LOCKED_FILE = "locked_file"


class FindingStatus(StrEnum):
    NEW = "new"
    APPROVED = "approved"
    REJECTED = "rejected"
    IGNORED = "ignored"


class FileOperationType(StrEnum):
    RENAME = "rename"
    MOVE = "move"
    DELETE = "delete"
    COPY = "copy"
    REPLACE = "replace"


class FileOperationStatus(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScannerRunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScannerTrigger(StrEnum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"


class BackupType(StrEnum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    PRE_RESTORE = "pre_restore"


class DeviceStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class AssetRegisteredVia(StrEnum):
    MANUAL = "manual"
    SCANNER = "scanner"
