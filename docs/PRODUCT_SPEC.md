# ProducerOS — Product Specification

> This document is the permanent, verbatim product specification for ProducerOS.
> It is the source of truth for scope, defaults, and non-negotiable constraints.
> Any future change to product behavior should be reconciled against this
> document, and material deviations should be recorded as an ADR in `docs/adr/`.

## 0. Summary

ProducerOS is a local-first music production management system for a
professional producer using FL Studio 2025 on Windows. It organizes
projects, versions, audio assets, metadata, contributors, rights, releases,
marketing plans, deadlines, delivery packages, and analytics. It ships a
responsive dashboard usable on Windows desktop browsers and Android phones
and tablets (including as an installable PWA), and it works fully without
API keys, cloud services, paid accounts, Docker, or any external
integration.

## 1. Non-negotiable product requirements

ProducerOS must be local-first, Windows-first, usable without Docker, usable
without external APIs, usable without internet after installation,
responsive on Android, installable as a PWA, safe with unreleased music,
reproducible from the GitHub repository, fully documented, fully testable
with synthetic data, and transferable to another person through GitHub.

The repository is the sole source of truth. ProducerOS does not rely on
undocumented local files, chat history, temporary Codex files, uncommitted
changes, developer-specific paths, developer-specific secrets, external
databases, cloud storage, manually installed JavaScript packages, or
CDN-hosted scripts, fonts, icons, or CSS. All runtime web assets are stored
locally in the repository or generated during the documented build.

## 2. Safety boundaries

ProducerOS must never: modify `.flp` files; interpret or reverse-engineer
`.flp` internals; overwrite existing music files; delete music files
automatically; rename or move files without an approved operation; upload
music to the internet; publish releases; send messages or emails; change
rights percentages automatically; claim that automated analysis replaces
professional listening; claim that a track will become successful; store
passwords in plaintext; or expose the application publicly by default.

All file-management proposals begin as dry runs. Destructive operations
require explicit confirmation and are logged.

## 3. Technology architecture

**Backend:** Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2.x, Alembic,
Pydantic, Pydantic Settings, SQLite with WAL mode by default,
PostgreSQL-compatible SQLAlchemy models where practical, Jinja2,
python-multipart, Watchdog for folder monitoring, Mutagen for audio
metadata where supported, standard-library `wave` support for WAV metadata
and synthetic fixtures, optional FFmpeg/FFprobe integration, Argon2
password hashing, structured application logging, Pytest, Ruff, mypy.

**Frontend:** server-rendered Jinja2, semantic HTML, local CSS, minimal
vanilla JavaScript, a PWA manifest, a service worker. No React, Next.js, or
Vue. No Node.js build requirement. No external CDN, fonts, or hosted icons.
Local SVG/CSS icons only. The application must remain maintainable by a
Python developer without a separate frontend toolchain.

**Packaging:** normal Python development installation, Windows PowerShell
setup and launch scripts, a PyInstaller-based portable Windows package, a
GitHub Actions workflow that builds a Windows release ZIP. Built
executables are never committed to Git history; build artifacts belong in
GitHub Actions and GitHub Releases.

## 4. Repository structure

See the top-level tree in this repository for the authoritative layout;
it mirrors the structure specified during the original build request
(`.github/`, `docs/`, `migrations/`, `packaging/`, `scripts/`, `src/produceros/`,
`tests/`, plus the top-level documentation and config files).

## 5. Permanent repository documentation

This specification lives at `docs/PRODUCT_SPEC.md`. Permanent rules for
future coding sessions live in `AGENTS.md`. Architecture decision records
live in `docs/adr/`.

## 6. Application data model

UUID primary keys and proper timestamps throughout. Entities: User,
PairedDevice, Artist, Project, Track, ProjectVersion, Asset, AssetVersion,
AudioAnalysis, Contributor, RightsShare, Clearance, Release, ChecklistRule,
ChecklistResult, MarketingCampaign, ContentAsset, MarketingDraft, Deadline,
DeliveryPreset, DeliveryPackage, DeliveryManifestItem, AnalyticsSource,
AnalyticsImport, AnalyticsMetric, Tag, ProjectTag, ScannerRoot, ScannerRun,
ScannerFinding, ApprovedFileOperation, AuditEvent, AppSetting, BackupRecord.

Database constraints are used where practical. Rights-share totals are
validated; a warning appears when totals are not exactly 100%. Ownership
percentages are never altered silently. See `docs/DATA_MODEL.md` for the
concrete schema as implemented.

## 7. Project workflow

Default states: `IDEA`, `ARRANGEMENT`, `PRODUCTION`, `VOCALS`, `EDITING`,
`MIX`, `MASTER`, `RELEASE_READY`, `SCHEDULED`, `RELEASED`, `ON_HOLD`,
`ARCHIVED`. Every state change is recorded in the audit log.
Administrators may configure which states are visible, but default system
identifiers are preserved.

## 8. Project catalog

Every project supports identity fields (working/final title, artist,
producer, featured artists, alternate titles, description, internal ID,
timestamps), musical information (BPM, key, time signature, genre,
subgenre, mood, energy, language, instruments, vocal style, similar
artists, tags, notes), production information (workflow state, FL Studio
project path, zipped project path, project root, current mix/master,
approval status, revision notes), rights information (writers, producers,
performers, publishers, master/composition owners, ownership percentages,
split confirmation, sample clearance, one-stop clearance, PRO registration
status), and release information (release type, date, distributor, ISRC,
UPC, explicit/clean status, artwork, description, readiness status).

## 9. File and folder scanner

Read-only by default; supports configurable Windows roots (e.g.
`D:\Music\Projects`, `D:\Music\Exports`, `D:\Music\Masters`). Detects the
extensions listed in the original specification and classifies findings as
new, changed, missing, exact/possible duplicates, new project/mix/master
versions, unexpected files, invalid paths, files outside approved roots,
and locked/unavailable files. Findings are stored in the database with an
approval workflow. The scanner never deletes, renames, moves, replaces, or
uploads automatically. Exact-duplicate detection uses content hashes;
filename/size/duration/metadata are used only as possible-duplicate
evidence.

## 10. Filename and version handling

Configurable filename patterns recognize common naming conventions
(artist/track/mix-or-master/version/date combinations, BPM/key
suffixes, `_FL_v##` project versions). Parsed data is normalized without
renaming the original file. Version metadata (asset type, version number,
date, artist, track, mix/master status, approval status, filename, path,
hash, size, modified date) is tracked; historical versions are never
overwritten, and exactly one "current" version per asset category is
permitted at a time.

## 11. Audio metadata and analysis

Works fully without FFmpeg using Mutagen and the standard-library `wave`
module (file type, duration, sample rate, bit depth, channels, size,
embedded title/artist/album/track number). When FFmpeg/FFprobe is present
it is auto-detected and optionally adds integrated loudness, loudness
range, true peak, and peak level. Metadata precedence distinguishes
user-confirmed, embedded, measured, and estimated values; user-confirmed
BPM/key are never overwritten automatically.

## 12. Release-readiness system

Configurable, deterministic (non-AI) release checklists per release type
(streaming single, EP, album, instrumental, remix, client delivery, beat
license, sync pitch, social-only release) covering audio, metadata,
rights, and marketing checks. Each check returns Passed, Failed, Warning,
Waived, or Blocking, with a recommended action.

## 13. Marketing workspace without external AI

A local template and rules engine builds editable drafts from confirmed
project data only (release announcement, social captions, descriptions,
hooks, outreach, press outline, and multi-week campaign plans). Generated
content never invents streaming numbers, awards, press coverage,
collaborations, credits, achievements, or quotes, and every item is marked
as a draft. Nothing is sent or published automatically. An optional local
LLM provider interface may exist but stays disabled and unnecessary for
full functionality.

## 14. Release calendar

Monthly calendar, weekly list, and mobile agenda views; overdue/upcoming
deadline tracking; filters by artist/project/campaign/type; `.ics` export.
No external calendar API is required.

## 15. Delivery packages

Client, sync, and distributor presets with completeness validation,
manifest generation, dry-run creation, required approval before copying
files, checksums, and audit logging. Existing packages are never
overwritten.

## 16. Analytics without platform APIs

Manual CSV import and manual entry across the metrics listed in the
original specification, with source/period/currency/raw-vs-calculated
tracking and data-quality warnings. Summaries by release, campaign,
channel, and content; no hit prediction and no causal claims without
evidence. CSV templates are provided.

## 17. Dashboard

A polished dark desktop dashboard and a first-class Android dashboard with
bottom navigation, 44×44px+ touch targets, no hover-only controls, no
horizontal scrolling, card-based mobile tables, a mobile filter drawer,
sticky primary actions, and full portrait/landscape support. Mobile bottom
navigation: Home, Projects, Releases, Calendar, More (Marketing, Scanner,
Deliveries, Analytics, Settings). The PWA is installable with local icons,
a service worker, an offline app shell, and a cached last-known dashboard
summary — clearly marked offline, and never implying full functionality
without the Windows host running.

## 18. Android and local-network access

Binds only to `127.0.0.1` by default. Desktop mode
(`scripts/run_desktop.ps1`) binds to localhost. LAN mode
(`scripts/run_lan.ps1`) binds only to a detected private-network address,
refuses public interfaces, shows the URL and a QR code, requires
authentication, uses expiring rate-limited pairing codes, stores paired
sessions securely, allows revocation, and shows a persistent LAN-mode
indicator. See `docs/ANDROID_PWA.md` for the connection walkthrough.

## 19. Authentication and security

Single-user local security model: first-run admin setup, Argon2 password
hashing, secure session cookies, CSRF protection, login and pairing rate
limiting, session expiration, device revocation, audit logging, safe error
handling, path/extension allowlisting, file-size limits, safe subprocess
arguments (no shell string construction from untrusted input), security
headers (CSP, referrer policy, clickjacking/MIME-sniffing protection), and
secret redaction from logs. No real secrets are committed; the application
generates its own local secret on first run and stores it outside the
repository.

## 20. Backups and data portability

SQLite backup/restore, JSON/CSV metadata export and import, checklist and
delivery-manifest export, backup history, backup verification, and restore
dry runs with explicit confirmation. Audio files are never included in
database backups; an optional manifest of external audio paths and hashes
is provided instead so the application (and its metadata) can move to
another Windows computer.

## 21. Local MCP server

Disabled by default, localhost-bound, requiring no external API. Provides
strictly-schema'd, read-only or draft-only tools (see `docs/MCP.md` for the
full list) with audit logging and no filesystem, deletion, publishing, or
messaging access. ProducerOS is fully functional with MCP disabled.

## 22. Demo mode

A synthetic catalog (two artists, six projects, versions, mix/master
assets, contributors, rights shares, checklists, campaigns, deadlines,
delivery packages, analytics, scanner findings) with programmatically
generated tiny WAV fixtures for tests. No copyrighted music or real
personal information. Exposed as an explicit "Load Demo Data" action.

## 23. Search and filtering

Global search plus filters (artist, project, genre, mood, BPM range, key,
stage, release status, rights status, clearance status, asset type,
missing assets, tags, date range) that work on desktop and Android, with
locally stored saved filters.

## 24. Accessibility

Targets WCAG 2.1 AA where practical: keyboard navigation, visible focus
states, proper labels, semantic headings, accessible validation errors,
adequate contrast, no color-only status meaning, reduced-motion support,
touch-friendly controls, accessible mobile navigation, and
screen-reader-friendly status messages.

## 25. Testing

Unit, integration, security, and end-to-end (Playwright, including a
mobile viewport) tests as enumerated in the original specification. See
`tests/` and the Testing section of `HANDOFF.md` for what is actually
implemented and what was run.

## 26–33. CI/CD, packaging, UX, reliability, sequencing, completion, validation, final report

See `.github/workflows/`, `packaging/`, `docs/RELEASE_PROCESS.md`,
`docs/INSTALL_WINDOWS.md`, `ROADMAP.md`, and `HANDOFF.md` for how these
sections were realized in the implemented system, including any deferred
items.
