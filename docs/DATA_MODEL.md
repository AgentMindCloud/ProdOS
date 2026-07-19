# Data Model

ProducerOS uses SQLAlchemy 2.x declarative models under `src/produceros/models/`,
one Alembic migration (`migrations/versions/657ecae8ddab_initial_schema.py`),
and SQLite (WAL mode) as the only runtime database -- see
[ADR 0004](adr/0004-sqlite-only-postgres-compatible-models.md) for why the
models are still written to be PostgreSQL-compatible.

Every table uses a UUID primary key (`UUIDPrimaryKeyMixin`, `db/base.py`)
and `created_at`/`updated_at` timestamps (`TimestampMixin`), stored via a
custom `UTCDateTime` type that always round-trips as UTC-aware regardless
of dialect (see [ADR 0004](adr/0004-sqlite-only-postgres-compatible-models.md)).

## Table groups

**Auth & devices** (`models/user.py`)
`User` (single admin account; Argon2 password hash, lockout counters),
`PairedDevice` (LAN-paired Android devices; pairing-code hash + session
token hash, never the raw values).

**Catalog** (`models/catalog.py`)
`Artist`, `Project` (the central entity: working/final title, state
machine, musical metadata, rights summary fields), `Track`,
`ProjectVersion` (FL project snapshots), `Tag`/`ProjectTag`.

**Assets** (`models/assets.py`)
`Asset` (a deliverable slot -- e.g. "the master") and `AssetVersion`
(each registered file for that slot, with approval status and a
"current version" flag), `AudioAnalysis` (Mutagen/wave/FFmpeg-derived
metadata per version).

**Rights** (`models/rights.py`)
`Contributor`, `RightsShare` (percentage splits; never auto-corrected,
only validated with a warning -- see `services/rights.py`), `Clearance`
(sample/interpolation clearance tracking).

**Release** (`models/release.py`)
`Release`, `ChecklistRule` (the ~30 deterministic readiness rules),
`ChecklistResult` (per-release, per-rule evaluation snapshot).

**Marketing** (`models/marketing.py`)
`MarketingCampaign`, `ContentAsset`, `MarketingDraft` (locally
template-generated copy -- see `docs/MCP.md`'s note on `marketing/llm_provider.py`
being a disabled stub, never called).

**Calendar** (`models/calendar.py`)
`Deadline` (release/marketing/deliverable deadlines; `.ics` export via
`services/calendar.export_ics`).

**Delivery** (`models/delivery.py`)
`DeliveryPreset` (client/sync/distributor presets), `DeliveryPackage`,
`DeliveryManifestItem` (dry-run manifest -> approve -> execute, with
checksums; see `docs/BACKUP_RESTORE.md` sibling doc for the parallel
backup/restore flow).

**Analytics** (`models/analytics.py`)
`AnalyticsSource`, `AnalyticsImport`, `AnalyticsMetric` -- CSV-imported,
never pulled from a platform API.

**Scanner & file safety** (`models/scanner.py`)
`ScannerRoot`, `ScannerRun`, `ScannerFinding` (read-only observations),
`ApprovedFileOperation` (the only path from a finding to an actual disk
change -- always starts `dry_run=True`, `PENDING_APPROVAL`; see
`docs/SECURITY_MODEL.md`).

**System** (`models/system.py`)
`AuditEvent` (append-only log of every state-changing action --
`services/audit.log_event`), `AppSetting` (key/value store, also used for
the session-invalidation timestamp trick, see
[ADR 0003](adr/0003-signed-cookies-not-server-side-sessions.md)),
`BackupRecord`.

## Deliberate non-FK columns

`Project.current_mix_asset_version_id` and `Asset`'s "current version"
pointer are plain `Uuid` columns, not `ForeignKey`-wrapped, to avoid a
three-table circular FK dependency (`Project -> AssetVersion -> Asset ->
Project`) that SQLite can't express cleanly. Full rationale in
[ADR 0001](adr/0001-plain-uuid-fk-shaped-columns.md). These are documented
inline in `models/catalog.py` and `models/assets.py` as well.

## Migrations

One Alembic revision currently exists (`657ecae8ddab_initial_schema.py`),
generated from the models above. `alembic.ini` has no hardcoded database
URL -- `migrations/env.py` resolves it from `produceros.config.get_settings()`
at runtime, so the same migration works against a developer's local data
dir, a test's isolated temp dir, or a frozen Windows build's
`%LOCALAPPDATA%\ProducerOS` data dir.

Run migrations via `produceros db-upgrade` (wraps Alembic's Python API,
not the `alembic` CLI, so a frozen build with no Python or `alembic` on
PATH can still migrate itself -- see
[ADR 0005](adr/0005-pyinstaller-onedir-frozen-path-resolution.md)).
`alembic check` (used in CI, see `.github/workflows/ci.yml`) verifies the
migration matches the current models with no drift.
