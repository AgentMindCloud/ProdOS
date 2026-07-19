"""Synthetic demo catalog (spec section 22).

Everything here is fictional: no real names, no copyrighted music, no
private information. Audio is a handful of tiny synthesized sine-wave WAV
files. Every row this module creates is recorded in a manifest
(AppSetting key ``demo_manifest``) so ``clean_demo_data`` can remove
exactly what demo mode added and nothing else.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from produceros.config import get_settings
from produceros.db.base import Base
from produceros.demo.audio_fixtures import generate_sine_wav
from produceros.delivery.packaging import create_package, generate_manifest
from produceros.delivery.presets import seed_default_presets
from produceros.marketing.campaigns import create_campaign, create_content_asset
from produceros.marketing.engine import generate_draft
from produceros.models.delivery import DeliveryPreset
from produceros.models.enums import (
    AnalyticsMetricType,
    AnalyticsSourceType,
    ApprovalStatus,
    AssetRegisteredVia,
    AssetType,
    CampaignType,
    ClearanceStatus,
    ClearanceType,
    ContentAssetType,
    ContributorRole,
    DeadlineType,
    ExplicitStatus,
    MarketingDraftType,
    ProjectState,
    ProRegistrationStatus,
    ReleaseType,
    RightsShareType,
    ScannerTrigger,
)
from produceros.models.release import Release
from produceros.models.scanner import ScannerFinding
from produceros.services import assets as asset_service
from produceros.services import catalog as catalog_service
from produceros.services import rights as rights_service
from produceros.services import settings as settings_service
from produceros.services.analytics import add_manual_metric, get_or_create_source
from produceros.services.calendar import create_deadline
from produceros.services.checklist import evaluate_release
from produceros.services.scanner import add_root, trigger_scan

DEMO_MANIFEST_KEY = "demo_manifest"


@dataclass
class _Manifest:
    entries: list[tuple[str, str]] = field(default_factory=list)

    def track(self, obj) -> None:
        self.entries.append((obj.__tablename__, str(obj.id)))

    def track_ref(self, table_name: str, entity_id) -> None:
        self.entries.append((table_name, str(entity_id)))


def _demo_audio_dir() -> Path:
    return get_settings().data_dir / "demo_audio"


def load_demo_data(session: Session) -> dict:
    manifest = _Manifest()
    audio_dir = _demo_audio_dir()

    # --- Artists -----------------------------------------------------
    artist_a = catalog_service.create_artist(session, name="Aurora Fields")
    artist_b = catalog_service.create_artist(session, name="Nightbloom Collective")
    manifest.track(artist_a)
    manifest.track(artist_b)

    project_specs = [
        dict(working_title="Glass Horizon", artist=artist_a, genre="Progressive House", mood="Uplifting", bpm=126, key="Am", state=ProjectState.MASTER),
        dict(working_title="Paper Lanterns", artist=artist_a, genre="Indie Pop", mood="Warm", bpm=112, key="C", state=ProjectState.MIX),
        dict(working_title="Static Bloom", artist=artist_b, genre="Synthwave", mood="Nostalgic", bpm=100, key="Fm", state=ProjectState.PRODUCTION),
        dict(working_title="Low Tide", artist=artist_b, genre="Ambient", mood="Calm", bpm=70, key="Dm", state=ProjectState.ARRANGEMENT),
        dict(working_title="Neon Freight", artist=artist_a, genre="Electro", mood="Driving", bpm=128, key="Gm", state=ProjectState.RELEASED),
        dict(working_title="Quiet Static", artist=artist_b, genre="Downtempo", mood="Introspective", bpm=90, key="Em", state=ProjectState.IDEA),
    ]

    projects = []
    for spec in project_specs:
        project = catalog_service.create_project(
            session, working_title=spec["working_title"], artist_id=spec["artist"].id,
            genre=spec["genre"], mood=spec["mood"], bpm=spec["bpm"], musical_key=spec["key"],
        )
        catalog_service.change_project_state(session, project, spec["state"], note="Demo data seed.")
        manifest.track(project)
        projects.append(project)

    # --- Assets, versions, and tiny synthetic audio -------------------
    for i, project in enumerate(projects[:4]):
        mix_path = generate_sine_wav(
            audio_dir / f"{project.internal_code}_mix_v01.wav", seconds=1.5, frequency_hz=220 + i * 20
        )
        mix_version = asset_service.register_asset_version(
            session, project=project, asset_type=AssetType.MIX, file_path=str(mix_path),
            registered_via=AssetRegisteredVia.MANUAL, mark_current=True,
        )
        manifest.track(mix_version.asset)
        manifest.track(mix_version)
        if mix_version.analysis is not None:
            manifest.track(mix_version.analysis)

        if project.state in (ProjectState.MASTER, ProjectState.RELEASE_READY, ProjectState.RELEASED):
            master_path = generate_sine_wav(
                audio_dir / f"{project.internal_code}_master_v01.wav", seconds=1.5, frequency_hz=440 + i * 20
            )
            master_version = asset_service.register_asset_version(
                session, project=project, asset_type=AssetType.MASTER, file_path=str(master_path),
                registered_via=AssetRegisteredVia.MANUAL, mark_current=True,
            )
            master_version.approval_status = ApprovalStatus.APPROVED
            manifest.track(master_version.asset)
            manifest.track(master_version)
            if master_version.analysis is not None:
                manifest.track(master_version.analysis)

    session.flush()

    # --- Contributors and rights shares --------------------------------
    for project in projects[:5]:
        writer = rights_service.add_contributor(session, project.id, name=f"{project.artist.name} (Writer)", role=ContributorRole.WRITER)
        producer = rights_service.add_contributor(session, project.id, name="Demo Producer", role=ContributorRole.PRODUCER)
        writer.approved = True
        producer.approved = True
        manifest.track(writer)
        manifest.track(producer)

        share_master_a = rights_service.add_rights_share(session, project.id, holder_name=project.artist.name, share_type=RightsShareType.MASTER, percentage=70, confirmed=True)
        share_master_b = rights_service.add_rights_share(session, project.id, holder_name="Demo Producer", share_type=RightsShareType.MASTER, percentage=30, confirmed=True)
        manifest.track(share_master_a)
        manifest.track(share_master_b)

        # Composition shares: correct 100% and confirmed for every project
        # except one deliberately-unconfirmed project, to demonstrate the
        # rights-share warning system in the demo catalog.
        is_unconfirmed_demo_case = project is projects[1]
        share_comp_a = rights_service.add_rights_share(
            session, project.id, holder_name=project.artist.name, share_type=RightsShareType.COMPOSITION,
            percentage=60, confirmed=not is_unconfirmed_demo_case,
        )
        share_comp_b = rights_service.add_rights_share(
            session, project.id, holder_name="Demo Producer", share_type=RightsShareType.COMPOSITION,
            percentage=40, confirmed=not is_unconfirmed_demo_case,
        )
        manifest.track(share_comp_a)
        manifest.track(share_comp_b)

        project.split_confirmed = not is_unconfirmed_demo_case
        project.master_owner = project.artist.name
        project.composition_owner = project.artist.name
        project.pro_registration_status = ProRegistrationStatus.REGISTERED

    clearance = rights_service.add_clearance(
        session, projects[2].id, clearance_type=ClearanceType.SAMPLE,
        description="Synth pad sample sourced from a royalty-free demo pack.",
    )
    rights_service.resolve_clearance(session, clearance, ClearanceStatus.CLEARED)
    manifest.track(clearance)
    session.flush()

    # --- Releases + checklists -----------------------------------------
    for project, release_type, explicit in [
        (projects[0], ReleaseType.STREAMING_SINGLE, ExplicitStatus.CLEAN),
        (projects[4], ReleaseType.STREAMING_SINGLE, ExplicitStatus.CLEAN),
    ]:
        project.explicit_status = explicit
        project.final_title = project.working_title
        project.release_description = f"{project.working_title} is a {project.genre.lower()} track exploring a {project.mood.lower()} mood."
        project.distributor = "Demo Distribution Co."
        project.isrc = f"US-DEM-26-{uuid.uuid4().hex[:5].upper()}"
        release = Release(
            project_id=project.id, release_type=release_type, title=project.working_title,
            release_date=date.today() + timedelta(days=21), distributor=project.distributor,
            isrc=project.isrc, explicit_status=explicit, description=project.release_description,
        )
        session.add(release)
        session.flush()
        manifest.track(release)
        # Tracked after the release (its parent): reversed deletion removes
        # these checklist results first, then the release row itself.
        for result in evaluate_release(session, release):
            manifest.track(result)

    # --- Marketing -------------------------------------------------------
    campaign = create_campaign(session, name=f"{projects[0].working_title} Launch", campaign_type=CampaignType.FOUR_WEEK, project_id=projects[0].id, artist_id=artist_a.id)
    manifest.track(campaign)
    content_asset = create_content_asset(session, title="Teaser clip idea", content_type=ContentAssetType.SHORT_VIDEO, project_id=projects[0].id, campaign_id=campaign.id)
    manifest.track(content_asset)
    for draft_type in (MarketingDraftType.RELEASE_ANNOUNCEMENT, MarketingDraftType.INSTAGRAM_CAPTION):
        draft = generate_draft(session, draft_type=draft_type, project=projects[0], campaign_id=campaign.id)
        manifest.track(draft)

    # --- Calendar ----------------------------------------------------
    deadline_specs = [
        (projects[0], DeadlineType.MASTER_APPROVAL, 3),
        (projects[0], DeadlineType.DISTRIBUTOR_SUBMISSION, 10),
        (projects[1], DeadlineType.MIX_DELIVERY, 5),
        (projects[2], DeadlineType.ARRANGEMENT_COMPLETE, 14),
        (projects[0], DeadlineType.PLAYLIST_PITCH, 18),
    ]
    for project, dtype, days in deadline_specs:
        deadline = create_deadline(
            session, title=f"{dtype.value.replace('_', ' ').title()} -- {project.working_title}",
            deadline_type=dtype, due_date=date.today() + timedelta(days=days), project_id=project.id,
        )
        manifest.track(deadline)

    # --- Delivery (left at "manifest generated" -- not executed, so demo
    # mode never copies files outside the app's own data directory) -------
    seed_default_presets(session)
    client_preset = session.scalar(select(DeliveryPreset).where(DeliveryPreset.preset_type == "client"))
    output_dir = get_settings().data_dir / "demo_deliveries" / projects[0].internal_code
    package = create_package(
        session, project=projects[0], preset=client_preset,
        name=f"{projects[0].working_title} -- Client Package", output_directory=str(output_dir),
    )
    generate_manifest(session, package)
    manifest.track(package)
    for item in package.items:
        manifest.track(item)

    # --- Analytics -----------------------------------------------------
    source = get_or_create_source(session, "Demo Streaming Report", AnalyticsSourceType.STREAMING)
    manifest.track(source)
    period_start = date.today() - timedelta(days=30)
    period_end = date.today()
    for metric_type, value, channel in [
        (AnalyticsMetricType.STREAMS, 4200, "Spotify"),
        (AnalyticsMetricType.LISTENERS, 1800, "Spotify"),
        (AnalyticsMetricType.SAVES, 210, "Spotify"),
        (AnalyticsMetricType.VIDEO_VIEWS, 950, "TikTok"),
    ]:
        metric = add_manual_metric(
            session, source=source, metric_type=metric_type, value=value,
            reporting_period_start=period_start, reporting_period_end=period_end,
            project_id=projects[0].id, channel=channel,
        )
        # Tracked in child-before-parent order: reversed deletion deletes
        # the metric first, then the AnalyticsImport row it belongs to.
        manifest.track_ref("analytics_imports", metric.import_id)
        manifest.track(metric)

    # --- Scanner: point a root at the demo audio dir and run a real scan ---
    generate_sine_wav(audio_dir / "Aurora Fields_Glass Horizon_MIX_v02_2026-06-01.wav", seconds=1.0, frequency_hz=300)
    root = add_root(session, path=str(audio_dir), label="Demo audio folder")
    manifest.track(root)
    run = trigger_scan(session, triggered_by=ScannerTrigger.MANUAL)
    manifest.track(run)
    for finding in session.scalars(select(ScannerFinding).where(ScannerFinding.run_id == run.id)):
        manifest.track(finding)

    session.flush()
    settings_service.set_setting(session, DEMO_MANIFEST_KEY, manifest.entries)

    return {
        "artists": 2,
        "projects": len(projects),
        "releases": 2,
        "deadlines": len(deadline_specs),
        "scanner_findings": run.findings_count,
        "delivery_packages": 1,
        "analytics_metrics": 4,
    }


_TABLE_TO_MODEL: dict[str, type] | None = None


def _table_to_model_map() -> dict[str, type]:
    global _TABLE_TO_MODEL
    if _TABLE_TO_MODEL is None:
        from produceros import models  # noqa: F401 -- ensures all models are imported/mapped

        _TABLE_TO_MODEL = {
            mapper.local_table.name: mapper.class_
            for mapper in Base.registry.mappers
            if mapper.local_table is not None
        }
    return _TABLE_TO_MODEL


def clean_demo_data(session: Session) -> int:
    """Remove exactly what ``load_demo_data`` created, in reverse order
    so foreign-key dependents are deleted before their parents."""
    raw = settings_service.get_setting(session, DEMO_MANIFEST_KEY, default=None)
    if not raw:
        return 0

    table_map = _table_to_model_map()
    removed = 0
    seen: set[tuple[str, str]] = set()
    for table_name, id_str in reversed(raw):
        key = (table_name, id_str)
        if key in seen:
            continue
        seen.add(key)
        model = table_map.get(table_name)
        if model is None:
            continue
        instance = session.get(model, uuid.UUID(id_str))
        if instance is not None:
            session.delete(instance)
            session.flush()
            removed += 1

    settings_service.delete_setting(session, DEMO_MANIFEST_KEY)

    import shutil

    demo_audio = _demo_audio_dir()
    if demo_audio.exists():
        shutil.rmtree(demo_audio, ignore_errors=True)
    demo_deliveries = get_settings().data_dir / "demo_deliveries"
    if demo_deliveries.exists():
        shutil.rmtree(demo_deliveries, ignore_errors=True)

    return removed
