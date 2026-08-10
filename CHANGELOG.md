# Changelog

All notable changes to ProducerOS. Format follows
[Keep a Changelog](https://keepachangelog.com/); versions follow SemVer
once tagged releases begin.

## [Unreleased]

### Added

- The current Windows installer is now committed to `installer/`, so
  downloading this repository as a ZIP yields something a non-technical
  person can double-click. See `installer/README.md` for the trade-off
  and `docs/BUILDING.md` for how to refresh it after a release.
- `docs/BUILDING.md`: how to build the installer (via CI or locally on
  Windows), what gates a release, and how to cut one.

### Fixed

- The `Security` workflow's dependency audit had failed on every run
  since the repository was created. `pip-audit --strict` was rejecting
  ProducerOS itself ("Dependency not found on PyPI and could not be
  audited") because it is a local, unpublished package -- not because of
  any vulnerability. It now audits `requirements.lock`, which also covers
  the dev/build tooling the previous environment scan never saw.

### Changed

- `packaging/README.md` and ADR 0006 no longer describe the installer as
  unverified: `windows-build.yml` has been observed passing on a real
  `windows-latest` runner, and v0.1.0 was built by that pipeline.

## [0.1.0] -- 2026-08-10

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
- **Packaging**: PyInstaller onedir spec (windowed, ProducerOS-branded
  `.ico`) + launcher for a standalone Windows exe, plus a real Inno Setup
  installer (`ProducerOS-Setup-X.Y.Z.exe`) -- per-user install with no
  admin/UAC prompt, Start Menu entry, optional desktop icon, proper
  uninstall via "Apps & features", and in-place upgrades across versions
  via a fixed AppId; a portable no-installer zip remains available as a
  secondary option. PowerShell scripts for setup/run/test/build/
  build-installer/backup/restore/demo-clean.
- **CI/CD**: GitHub Actions for lint+type+test matrix (Ubuntu/Windows),
  security scanning (pip-audit, gitleaks, bandit, repo hygiene), a
  Windows build that compiles the installer and smoke-tests the full
  real-world path (silent install, shortcut creation, launch, silent
  uninstall with data-directory preservation) plus SBOM + checksummed
  artifacts, and tag-driven release publishing with the installer as the
  headline download.
- **Tests**: 123 tests -- unit, integration (real HTTP), security, and
  Playwright e2e (real Chromium, desktop + mobile viewports).
- **Docs**: full documentation set under `docs/` (user/admin/install/
  Android/backup/release-process/data-model/security/troubleshooting/MCP),
  six ADRs, real captured screenshots, and root-level
  README/ARCHITECTURE/AGENTS/CONTRIBUTING/SECURITY/HANDOFF/ROADMAP.

### Added (review pass)

- **Single-instance behaviour**: launching ProducerOS while it is already
  running now re-opens it in the browser instead of failing to bind.
- **`GET /healthz`**: unauthenticated liveness probe (app name + version
  only), used to tell "ProducerOS is already running here" apart from
  "another program owns this port", which now produces an actionable
  error rather than a silent exit.
- **Settings -> Close ProducerOS**: an in-app quit. A windowed build has
  no console and no window, so without it the only way to stop the
  server was Task Manager -- and a running instance holds the files an
  update needs to replace.

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
- A windowed (`console=False`) PyInstaller build gets `sys.stdout`/
  `sys.stderr` of `None` from Windows, which would have crashed on the
  first `print()` or log line; the launcher now redirects both to a null
  sink before anything else runs.
- Double-clicking the desktop icon while ProducerOS was already running
  raised `SystemExit(1)` from uvicorn's failed bind. `launcher.py`
  deliberately re-raises `SystemExit` without a message box, so in a
  windowed build the user saw nothing at all -- no console, no error, no
  browser. This was the single most likely way for the app to look
  broken, since closing the browser tab does not stop the server.
- The browser was opened after a fixed 1-second sleep, which could race
  server startup on a slow machine and land the user on a "can't reach
  this site" page; it now waits for the port to actually accept
  connections.
- Restoring a backup from the web UI replaced the database file while the
  request's own SQLAlchemy session still held it open. POSIX allows that;
  Windows does not, so restore -- a data-recovery path -- would have
  failed there. The session is now closed first, and the swap stages a
  copy and `os.replace`s it into place with a retry.
