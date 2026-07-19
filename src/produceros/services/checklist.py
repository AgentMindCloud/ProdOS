"""Deterministic release-readiness checklist engine (spec section 12).

No AI, no heuristics beyond simple data lookups: every rule is a small
pure function of the project/release's confirmed data. Results are
Passed / Failed-as-Blocking / Failed-as-Warning / Waived, exactly as
specified. Waiving a blocking result is always an explicit, audited user
action -- never automatic.

Default rules are seeded once (idempotently, keyed by ``code``) and
flagged ``is_system_default`` so an admin can deactivate but not silently
lose the baseline rule set, mirroring the project-state preservation rule
in spec section 7.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from produceros.models.assets import Asset, AssetVersion
from produceros.models.catalog import Project
from produceros.models.enums import (
    AssetType,
    ChecklistCategory,
    ChecklistSeverity,
    ChecklistStatus,
    ClearanceStatus,
    ContentAssetType,
    ExplicitStatus,
    ReleaseType,
)
from produceros.models.marketing import ContentAsset, MarketingCampaign
from produceros.models.release import ChecklistResult, ChecklistRule, Release
from produceros.models.rights import Contributor
from produceros.services.audit import log_event
from produceros.services.rights import validate_rights_shares

VALID_SAMPLE_RATES = {44100, 48000, 88200, 96000, 176400, 192000}
VALID_BIT_DEPTHS = {16, 24, 32}

CheckResult = tuple[bool | None, str, str]  # (satisfied_or_none_for_n/a, detail, recommended_action)
CheckFn = Callable[[Session, Project, Release], CheckResult]


def _current_asset_version(session: Session, project_id: uuid.UUID, asset_type: AssetType) -> AssetVersion | None:
    asset = session.scalar(
        select(Asset).where(Asset.project_id == project_id, Asset.asset_type == asset_type)
    )
    if asset is None:
        return None
    return session.scalar(
        select(AssetVersion).where(AssetVersion.asset_id == asset.id, AssetVersion.is_current.is_(True))
    )


def _check_master_approved(session: Session, project: Project, release: Release) -> CheckResult:
    version = _current_asset_version(session, project.id, AssetType.MASTER)
    if version and version.approval_status.value == "approved":
        return True, "An approved current master is registered.", ""
    return False, "No approved master is registered.", "Register and approve a master under Assets."


def _check_master_wav(session: Session, project: Project, release: Release) -> CheckResult:
    version = _current_asset_version(session, project.id, AssetType.MASTER)
    if version and version.original_filename.lower().endswith(".wav"):
        return True, "Current master is a WAV file.", ""
    if version is None:
        return False, "No current master registered.", "Register a WAV master under Assets."
    return False, f"Current master is '{version.original_filename}', not a WAV.", "Register a WAV master."


def _check_valid_sample_rate(session: Session, project: Project, release: Release) -> CheckResult:
    version = _current_asset_version(session, project.id, AssetType.MASTER)
    if version is None or version.analysis is None or version.analysis.sample_rate is None:
        return None, "Sample rate unknown (no analysis available).", "Register a master and let ProducerOS analyze it."
    ok = version.analysis.sample_rate in VALID_SAMPLE_RATES
    return ok, f"Master sample rate: {version.analysis.sample_rate} Hz.", "Deliver a standard sample rate (44.1/48/88.2/96 kHz)."


def _check_valid_bit_depth(session: Session, project: Project, release: Release) -> CheckResult:
    version = _current_asset_version(session, project.id, AssetType.MASTER)
    if version is None or version.analysis is None or version.analysis.bit_depth is None:
        return None, "Bit depth unknown (no analysis available).", "Register a master and let ProducerOS analyze it."
    ok = version.analysis.bit_depth in VALID_BIT_DEPTHS
    return ok, f"Master bit depth: {version.analysis.bit_depth}-bit.", "Deliver 16/24/32-bit audio."


def _requires_instrumental(release: Release) -> bool:
    return release.release_type in {
        ReleaseType.STREAMING_SINGLE, ReleaseType.EP, ReleaseType.ALBUM, ReleaseType.REMIX,
    }


def _check_instrumental(session: Session, project: Project, release: Release) -> CheckResult:
    if not _requires_instrumental(release):
        return None, "Instrumental not required for this release type.", ""
    version = _current_asset_version(session, project.id, AssetType.INSTRUMENTAL)
    if version:
        return True, "Instrumental is registered.", ""
    return False, "No instrumental registered.", "Register an instrumental under Assets."


def _check_clean_version(session: Session, project: Project, release: Release) -> CheckResult:
    if project.explicit_status != ExplicitStatus.EXPLICIT:
        return None, "Clean version not required (release is not marked explicit).", ""
    version = _current_asset_version(session, project.id, AssetType.CLEAN_VERSION)
    if version:
        return True, "Clean version is registered.", ""
    return False, "Release is explicit but no clean version is registered.", "Register a clean version under Assets."


def _check_acapella(session: Session, project: Project, release: Release) -> CheckResult:
    if release.release_type not in {ReleaseType.SYNC_PITCH, ReleaseType.REMIX}:
        return None, "Acapella not required for this release type.", ""
    version = _current_asset_version(session, project.id, AssetType.ACAPELLA)
    if version:
        return True, "Acapella is registered.", ""
    return False, "No acapella registered.", "Register an acapella under Assets."


def _check_stems(session: Session, project: Project, release: Release) -> CheckResult:
    if release.release_type not in {ReleaseType.SYNC_PITCH, ReleaseType.CLIENT_DELIVERY}:
        return None, "Stem package not required for this release type.", ""
    version = _current_asset_version(session, project.id, AssetType.STEMS)
    if version:
        return True, "Stem package is registered.", ""
    return False, "No stem package registered.", "Register a stems package under Assets."


def _check_final_title(session: Session, project: Project, release: Release) -> CheckResult:
    return bool(project.final_title), f"Final title: '{project.final_title or 'not set'}'.", "Set the final title on the project."


def _check_artist(session: Session, project: Project, release: Release) -> CheckResult:
    return project.artist_id is not None, "Primary artist assignment.", "Assign a primary artist to the project."


def _check_featured_artists_confirmed(session: Session, project: Project, release: Release) -> CheckResult:
    if not project.featured_artists:
        return None, "No featured artists on this release.", ""
    ok = bool(project.split_confirmed)
    return ok, f"{len(project.featured_artists)} featured artist(s) listed.", "Confirm splits with featured artists."


def _check_genre(session: Session, project: Project, release: Release) -> CheckResult:
    return bool(project.genre), f"Genre: '{project.genre or 'not set'}'.", "Set a genre on the project."


def _check_language(session: Session, project: Project, release: Release) -> CheckResult:
    return bool(project.language), f"Language: '{project.language or 'not set'}'.", "Set a language on the project."


def _check_explicit_status(session: Session, project: Project, release: Release) -> CheckResult:
    ok = project.explicit_status != ExplicitStatus.NOT_SET
    return ok, f"Explicit status: {project.explicit_status.value}.", "Set explicit/clean status on the project."


def _check_contributors_entered(session: Session, project: Project, release: Release) -> CheckResult:
    count = session.scalar(select(Contributor).where(Contributor.project_id == project.id).limit(1))
    return count is not None, "Contributors recorded." if count else "No contributors recorded.", "Add writers/producers/performers under Rights."


def _check_rights_shares_validated(session: Session, project: Project, release: Release) -> CheckResult:
    validations = validate_rights_shares(session, project.id)
    if not validations:
        return False, "No rights shares recorded.", "Add master and composition rights shares under Rights."
    ok = all(v.is_exactly_100 and v.all_confirmed for v in validations)
    detail = "; ".join(v.warning or f"{v.share_type.value} shares confirmed at 100%." for v in validations)
    return ok, detail, "Reconcile and confirm rights shares so each type totals exactly 100%."


def _check_distributor_recorded(session: Session, project: Project, release: Release) -> CheckResult:
    if release.release_type == ReleaseType.SOCIAL_ONLY:
        return None, "Distributor not applicable for a social-only release.", ""
    return bool(release.distributor), f"Distributor: '{release.distributor or 'not set'}'.", "Record the distributor for this release."


def _check_isrc_status(session: Session, project: Project, release: Release) -> CheckResult:
    if release.release_type == ReleaseType.SOCIAL_ONLY:
        return None, "ISRC not applicable for a social-only release.", ""
    return bool(release.isrc), f"ISRC: '{release.isrc or 'not recorded'}'.", "Record an ISRC for this release."


def _check_upc_status(session: Session, project: Project, release: Release) -> CheckResult:
    if release.release_type not in {ReleaseType.EP, ReleaseType.ALBUM, ReleaseType.STREAMING_SINGLE}:
        return None, "UPC not applicable for this release type.", ""
    return bool(release.upc), f"UPC: '{release.upc or 'not recorded'}'.", "Record a UPC for this release."


def _check_splits_confirmed(session: Session, project: Project, release: Release) -> CheckResult:
    return bool(project.split_confirmed), "Split confirmation flag.", "Confirm splits with all contributors under Rights."


def _check_sample_clearance(session: Session, project: Project, release: Release) -> CheckResult:
    status = project.sample_clearance_status
    if status == ClearanceStatus.NOT_APPLICABLE:
        return None, "No sample clearance required.", ""
    if status == ClearanceStatus.CLEARED:
        return True, "Sample clearance resolved (cleared).", ""
    if status == ClearanceStatus.DENIED:
        return False, "Sample clearance was DENIED.", "This release cannot proceed with a denied sample clearance."
    return False, "Sample clearance is unresolved.", "Resolve sample clearance under Rights."


def _check_master_owner(session: Session, project: Project, release: Release) -> CheckResult:
    return bool(project.master_owner), f"Master owner: '{project.master_owner or 'not set'}'.", "Record the master owner."


def _check_composition_owner(session: Session, project: Project, release: Release) -> CheckResult:
    return bool(project.composition_owner), f"Composition owner: '{project.composition_owner or 'not set'}'.", "Record the composition owner."


def _check_collaborator_approval(session: Session, project: Project, release: Release) -> CheckResult:
    contributors = list(session.scalars(select(Contributor).where(Contributor.project_id == project.id)))
    if not contributors:
        return None, "No collaborators to approve.", ""
    ok = all(c.approved for c in contributors)
    return ok, f"{sum(1 for c in contributors if c.approved)}/{len(contributors)} collaborators approved.", "Record collaborator approval under Rights."


def _check_cover_artwork(session: Session, project: Project, release: Release) -> CheckResult:
    version = _current_asset_version(session, project.id, AssetType.ARTWORK)
    return version is not None, "Cover artwork registered." if version else "No cover artwork registered.", "Register cover artwork under Assets."


def _check_release_description(session: Session, project: Project, release: Release) -> CheckResult:
    return bool(release.description), "Release description present." if release.description else "No release description.", "Write a release description."


def _check_release_date(session: Session, project: Project, release: Release) -> CheckResult:
    return release.release_date is not None, "Release date set." if release.release_date else "No release date set.", "Set a release date."


def _check_campaign_exists(session: Session, project: Project, release: Release) -> CheckResult:
    exists = session.scalar(
        select(MarketingCampaign).where(MarketingCampaign.project_id == project.id).limit(1)
    )
    return exists is not None, "Marketing campaign exists." if exists else "No marketing campaign created.", "Create a marketing campaign."


def _check_short_form_asset(session: Session, project: Project, release: Release) -> CheckResult:
    exists = session.scalar(
        select(ContentAsset).where(
            ContentAsset.project_id == project.id,
            ContentAsset.content_type.in_(
                [ContentAssetType.SHORT_VIDEO, ContentAssetType.STORY, ContentAssetType.CAROUSEL]
            ),
        ).limit(1)
    )
    return exists is not None, "At least one short-form asset exists." if exists else "No short-form content asset yet.", "Add a short-form content asset under Marketing."


def _check_smart_link_status(session: Session, project: Project, release: Release) -> CheckResult:
    exists = session.scalar(
        select(ContentAsset).where(
            ContentAsset.project_id == project.id,
            ContentAsset.title.ilike("%smart link%"),
        ).limit(1)
    )
    if exists:
        return True, "Smart-link status recorded.", ""
    return False, "Smart-link status not recorded.", "Add a 'Smart Link' content asset under Marketing (mark not applicable if none is used)."


@dataclass
class RuleDefinition:
    code: str
    category: ChecklistCategory
    description: str
    severity: ChecklistSeverity
    check: CheckFn
    release_type: ReleaseType | None = None


DEFAULT_RULES: list[RuleDefinition] = [
    RuleDefinition("audio.master_approved", ChecklistCategory.AUDIO, "Approved master exists", ChecklistSeverity.BLOCKING, _check_master_approved),
    RuleDefinition("audio.master_wav_exists", ChecklistCategory.AUDIO, "WAV master exists", ChecklistSeverity.RECOMMENDED, _check_master_wav),
    RuleDefinition("audio.valid_sample_rate", ChecklistCategory.AUDIO, "Valid sample rate", ChecklistSeverity.WARNING, _check_valid_sample_rate),
    RuleDefinition("audio.valid_bit_depth", ChecklistCategory.AUDIO, "Valid bit depth", ChecklistSeverity.WARNING, _check_valid_bit_depth),
    RuleDefinition("audio.instrumental_exists", ChecklistCategory.AUDIO, "Instrumental exists when required", ChecklistSeverity.RECOMMENDED, _check_instrumental),
    RuleDefinition("audio.clean_version_exists", ChecklistCategory.AUDIO, "Clean version exists when required", ChecklistSeverity.BLOCKING, _check_clean_version),
    RuleDefinition("audio.acapella_exists", ChecklistCategory.AUDIO, "Acapella exists when required", ChecklistSeverity.RECOMMENDED, _check_acapella),
    RuleDefinition("audio.stems_exist", ChecklistCategory.AUDIO, "Stem package exists when required", ChecklistSeverity.RECOMMENDED, _check_stems),
    RuleDefinition("metadata.final_title_exists", ChecklistCategory.METADATA, "Final title exists", ChecklistSeverity.BLOCKING, _check_final_title),
    RuleDefinition("metadata.artist_exists", ChecklistCategory.METADATA, "Artist exists", ChecklistSeverity.BLOCKING, _check_artist),
    RuleDefinition("metadata.featured_artists_confirmed", ChecklistCategory.METADATA, "Featured artists confirmed", ChecklistSeverity.RECOMMENDED, _check_featured_artists_confirmed),
    RuleDefinition("metadata.genre_exists", ChecklistCategory.METADATA, "Genre exists", ChecklistSeverity.WARNING, _check_genre),
    RuleDefinition("metadata.language_exists", ChecklistCategory.METADATA, "Language exists", ChecklistSeverity.WARNING, _check_language),
    RuleDefinition("metadata.explicit_status_set", ChecklistCategory.METADATA, "Explicit status set", ChecklistSeverity.BLOCKING, _check_explicit_status),
    RuleDefinition("metadata.contributors_entered", ChecklistCategory.METADATA, "Contributors entered", ChecklistSeverity.RECOMMENDED, _check_contributors_entered),
    RuleDefinition("metadata.rights_shares_validated", ChecklistCategory.METADATA, "Rights shares validated", ChecklistSeverity.RECOMMENDED, _check_rights_shares_validated),
    RuleDefinition("metadata.distributor_recorded", ChecklistCategory.METADATA, "Distributor recorded where applicable", ChecklistSeverity.WARNING, _check_distributor_recorded),
    RuleDefinition("metadata.isrc_status_recorded", ChecklistCategory.METADATA, "ISRC status recorded", ChecklistSeverity.WARNING, _check_isrc_status),
    RuleDefinition("metadata.upc_status_recorded", ChecklistCategory.METADATA, "UPC status recorded", ChecklistSeverity.WARNING, _check_upc_status),
    RuleDefinition("rights.splits_confirmed", ChecklistCategory.RIGHTS, "Splits confirmed", ChecklistSeverity.BLOCKING, _check_splits_confirmed),
    RuleDefinition("rights.sample_clearance_resolved", ChecklistCategory.RIGHTS, "Sample clearance resolved", ChecklistSeverity.BLOCKING, _check_sample_clearance),
    RuleDefinition("rights.master_owner_recorded", ChecklistCategory.RIGHTS, "Master owner recorded", ChecklistSeverity.RECOMMENDED, _check_master_owner),
    RuleDefinition("rights.composition_owner_recorded", ChecklistCategory.RIGHTS, "Composition owner recorded", ChecklistSeverity.RECOMMENDED, _check_composition_owner),
    RuleDefinition("rights.collaborator_approval_recorded", ChecklistCategory.RIGHTS, "Collaborator approval recorded", ChecklistSeverity.WARNING, _check_collaborator_approval),
    RuleDefinition("marketing.cover_artwork_exists", ChecklistCategory.MARKETING, "Cover artwork exists", ChecklistSeverity.BLOCKING, _check_cover_artwork),
    RuleDefinition("marketing.release_description_exists", ChecklistCategory.MARKETING, "Release description exists", ChecklistSeverity.RECOMMENDED, _check_release_description),
    RuleDefinition("marketing.release_date_exists", ChecklistCategory.MARKETING, "Release date exists", ChecklistSeverity.BLOCKING, _check_release_date),
    RuleDefinition("marketing.campaign_exists", ChecklistCategory.MARKETING, "Marketing campaign exists", ChecklistSeverity.WARNING, _check_campaign_exists),
    RuleDefinition("marketing.short_form_asset_exists", ChecklistCategory.MARKETING, "At least one short-form asset exists", ChecklistSeverity.WARNING, _check_short_form_asset),
    RuleDefinition("marketing.smart_link_status_recorded", ChecklistCategory.MARKETING, "Smart-link status recorded", ChecklistSeverity.WARNING, _check_smart_link_status),
]

_RULE_REGISTRY: dict[str, RuleDefinition] = {r.code: r for r in DEFAULT_RULES}


def seed_default_rules(session: Session) -> None:
    existing_codes = set(session.scalars(select(ChecklistRule.code)))
    for definition in DEFAULT_RULES:
        if definition.code in existing_codes:
            continue
        session.add(
            ChecklistRule(
                release_type=definition.release_type,
                category=definition.category,
                code=definition.code,
                description=definition.description,
                severity=definition.severity,
                is_active=True,
                is_system_default=True,
            )
        )
    session.flush()


def evaluate_release(session: Session, release: Release, *, user_id: uuid.UUID | None = None) -> list[ChecklistResult]:
    project = session.get(Project, release.project_id)
    if project is None:
        raise ValueError("Release has no associated project.")

    seed_default_rules(session)
    rules = list(
        session.scalars(
            select(ChecklistRule).where(
                ChecklistRule.is_active.is_(True),
                (ChecklistRule.release_type.is_(None)) | (ChecklistRule.release_type == release.release_type),
            )
        )
    )

    # Replace any prior results for this release so re-evaluation is idempotent.
    session.query(ChecklistResult).filter(ChecklistResult.release_id == release.id).delete()

    results: list[ChecklistResult] = []
    for rule in rules:
        definition = _RULE_REGISTRY.get(rule.code)
        if definition is None:
            continue
        satisfied, detail, recommended_action = definition.check(session, project, release)
        if satisfied is None:
            status = ChecklistStatus.WAIVED
        elif satisfied:
            status = ChecklistStatus.PASSED
        elif rule.severity == ChecklistSeverity.BLOCKING:
            status = ChecklistStatus.BLOCKING
        else:
            status = ChecklistStatus.WARNING

        result = ChecklistResult(
            release_id=release.id,
            rule_id=rule.id,
            status=status,
            detail=detail,
            recommended_action=recommended_action or None,
            evaluated_at=datetime.now(timezone.utc),
        )
        session.add(result)
        results.append(result)

    session.flush()
    release.readiness_status = summarize_status(results)
    session.flush()
    log_event(
        session,
        event_type="release.readiness_evaluated",
        summary=f"Release readiness evaluated for '{release.title}': {release.readiness_status}.",
        user_id=user_id,
        entity_type="Release",
        entity_id=release.id,
    )
    return results


def summarize_status(results: list[ChecklistResult]) -> str:
    if any(r.status == ChecklistStatus.BLOCKING for r in results):
        return "blocking"
    if any(r.status in (ChecklistStatus.FAILED, ChecklistStatus.WARNING) for r in results):
        return "warning"
    return "ready"


def waive_result(
    session: Session, result: ChecklistResult, *, user_id: uuid.UUID, reason: str
) -> ChecklistResult:
    result.status = ChecklistStatus.WAIVED
    result.waived_by = user_id
    result.waived_reason = reason
    session.flush()
    log_event(
        session,
        event_type="release.checklist_waived",
        summary=f"Checklist result waived: {reason}",
        user_id=user_id,
        entity_type="ChecklistResult",
        entity_id=result.id,
    )
    return result
