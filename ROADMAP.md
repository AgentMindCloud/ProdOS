# Roadmap

Ideas deliberately deferred from the initial build, roughly ordered.
Nothing here is committed work; each item must still respect the
constraints in `AGENTS.md` (local-first, no external services, no
automatic file mutation, no invented marketing content).

## Near-term polish

- **Audit-log page**: `AuditEvent` rows are written everywhere but only
  inspectable via the database today (`docs/ADMIN_GUIDE.md`).
- **Scheduled backups in-app**: currently done via Task Scheduler +
  `scripts/backup.ps1`; a built-in scheduler with retention policy would
  remove the external moving part.
- **Scanner watch mode**: use the already-bundled `watchdog` dependency
  for opt-in continuous observation (still read-only) instead of manual
  scan runs.
- **Persistent pairing rate-limiter**: the in-process limiter resets on
  restart (`docs/SECURITY_MODEL.md`); back it with the database.

## Features

- **Waveform previews / in-browser audio playback** of registered
  versions (local files only, streamed by the local server).
- **A/B version comparison** with the loudness metrics already collected
  by `audio/`.
- **Checklist rule editor**: rules are seeded and deterministic; letting
  the producer add/disable rules per release type fits the design.
- **Richer analytics**: trend charts per project/period from the imported
  CSV metrics (rendered locally, no chart CDN).
- **Multi-track release support** deepening: per-track checklist results
  and delivery manifests.
- **`.ics` subscription feed** (read-only local URL) in addition to file
  export.

## Platform

- **PostgreSQL option** for a self-hosted multi-device setup -- models
  are already dialect-clean (ADR 0004); needs a driver, a config branch,
  and migration testing.
- **Code-signed Windows builds** once a certificate exists;
  `windows-build.yml` already produces the artifact + SBOM + checksum.
- **Linux/macOS packaging**: the app already runs from source anywhere
  Python 3.12 runs; PyInstaller specs for other hosts would formalize it.

## Explicitly not planned

Cloud sync, streaming-platform API integrations, AI-generated marketing
copy, automatic publishing/distribution, and anything that uploads the
producer's audio -- these contradict the product's core constraints
rather than merely being unbuilt.
