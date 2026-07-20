# Changelog

All notable changes to ProducerOS. Format follows
[Keep a Changelog](https://keepachangelog.com/); versions follow SemVer
once tagged releases begin.

## [Unreleased] -- 0.1.0 (initial build)

The complete initial implementation of ProducerOS per
`docs/PRODUCT_SPEC.md`.

### Added

- **Core application**: 34-table SQLAlchemy data model with Alembic
  migrations; catalog (artists, projects, tracks, workflow state
  machine), asset versioning with "current version" tracking, rights
  shares with validate-but-never-auto-correct semantics, clearances,
  deterministic ~30-rule release-readiness checklist, marketing workspace
  with 16 local templates (no AI), release calendar with `.ics` export,
  delivery packages (dry-run manifest -> approve -> execute, refuses to
  overwrite), analytics CSV import, full audit log, backup/verify/restore
  with pre-restore safety copy.
- **Web app**: server-rendered dark-theme responsive dashboard (desktop
  sidebar / mobile bottom nav), installable PWA with offline app shell,
  first-run setup, search, settings.
- **Security**: Argon2 auth with lockout, signed session cookies with
  revocation, double-submit CSRF via middleware, security headers + CSP,
  LAN device pairing (QR + rate-limited single-use codes, instant
  revocation), read-only scanner with approval-gated file operations,
  path/symlink containment, secret-redacting logs.
- **MCP server**: optional, disabled-by-default, localhost-only FastMCP
  server with 14 read/draft-only audited tools.
- **Demo mode**: synthetic catalog (real generated WAV fixtures, real
  scanner run) with precise manifest-based cleanup.
- **Packaging**: PyInstaller onedir spec + launcher for a standalone
  Windows exe; PowerShell scripts for setup/run/test/build/backup/
  restore/demo-clean.
- **CI/CD**: GitHub Actions for lint+type+test matrix (Ubuntu/Windows),
  security scanning (pip-audit, gitleaks, bandit, repo hygiene), Windows
  build with smoke test + SBOM + checksummed artifact, and tag-driven
  release publishing.
- **Tests**: 123 tests -- unit, integration (real HTTP), security, and
  Playwright e2e (real Chromium, desktop + mobile viewports).
- **Docs**: full documentation set under `docs/` (user/admin/install/
  Android/backup/release-process/data-model/security/troubleshooting/MCP),
  five ADRs, real captured screenshots, and root-level
  README/ARCHITECTURE/AGENTS/CONTRIBUTING/SECURITY/HANDOFF/ROADMAP.

### Fixed (during the initial build, caught by this repo's own tests)

- Filename parser: `\b` word-boundary regexes silently failed next to
  underscores, mis-parsing every spec example filename; replaced with
  explicit lookarounds.
- `restore_dry_run` crashed instead of failing cleanly on a non-SQLite
  file.
- SQLite returned naive datetimes for `DateTime(timezone=True)` columns,
  crashing tz-aware comparisons (e.g. the login-lockout check); added the
  `UTCDateTime` decorator used by every timestamp column.
- QR generation for LAN pairing broke without Pillow installed
  (`PyPNGImage.save()` rejects the `format` kwarg).
- Most list pages (contributors, rights, releases, calendar, devices,
  marketing, search, delivery, backups) were invisible on desktop due to
  a mobile-first `.record-card { display:none }` default.
- Frozen builds couldn't find bundled migrations (PyInstaller 6 puts
  `datas` under `_internal/`; now resolved via `sys._MEIPASS`).
- The frozen launcher discarded all CLI arguments (`--mode`, `--port`,
  `--no-browser` had no effect).
- The MCP server was fully built but never started -- `produceros run`
  now launches it when `mcp_enabled` is set.
