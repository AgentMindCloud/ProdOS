# ADR 0007: Static public website alongside the offline desktop app

- Date: 2026-09-09
- Status: implemented, approved and published at https://prodos.tech/; see WEBSITE_LAUNCH.md for verification limits

## Context

The owner wants a website available for a producer friend's first trial so
the friend can share the idea and download the Windows app. `prodos.tech`
is registered and the account has active Business Web Hosting. Moving the
Python desktop backend to a public server would disconnect it from the
producer's local music paths and require a different security/product model.

## Decision

Build a separate static website in `website/`, with a small browser-only
sample workflow, explicit preview download, installation guide, release
notes, feedback link and share controls. Store one reviewed Windows ZIP on
the same website for the initial launch. Generate the deployable directory
from an allowlist with `scripts/build_website.py`, including checksums.

All demo projects are synthetic. The demo's state stays in browser memory;
its audio is an original synthesized loop generated at build time. It never
requests a visitor's music files. Existing desktop app routes, local binding,
music-file approvals, authentication and offline behavior remain unchanged.

Use ordinary static hosting. There is no public Python backend, user database,
cloud music storage, automatic publishing, telemetry, billing, online licence
check or silent updater. The public website is not a new runtime dependency
of ProducerOS. Optional desktop network features need a separate decision.

## Consequences

The site is inexpensive to operate and simple to move between hosts. Download
traffic consumes bandwidth; storage holds one copy of each retained release.
Build-time release metadata and checksums must change together with a new
binary. The initial 0.2.0 download is an unsigned portable preview, not a new
installer or a clean-machine-certified release.

The website can be updated without migrating the producer's app database.
Public uploads require a reviewed archive and a live HTTPS/download check.
Adding a community database or accounts later is outside this decision.
