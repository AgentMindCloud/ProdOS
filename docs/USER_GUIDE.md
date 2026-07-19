# User Guide

This is a walkthrough of ProducerOS's features from a producer's point of
view. For install steps see `docs/INSTALL_WINDOWS.md`; for phone access
see `docs/ANDROID_PWA.md`; for admin/operational topics (backups,
releases process, MCP) see the sibling docs linked at the end.

## First run

Launching ProducerOS for the first time takes you to `/setup` to create
your one admin account (display name, username, password -- 10+
characters). There's no separate "install wizard": the database is
created and migrated automatically, and you're logged straight in
afterward.

Want to explore with realistic sample data first? Run
`ProducerOS.exe demo-load` (or `.\scripts\run_desktop.ps1` then use the
CLI from another terminal) to load 2 artists, 6 projects at various
workflow stages, real tiny synthetic audio files, rights shares, a
release with an evaluated checklist, marketing drafts, calendar
deadlines, and a scanner run against real generated files. Remove it
later with `demo-clean` (`.\scripts\clean_demo.ps1`) -- it removes
exactly what was loaded, nothing you've created yourself.

## Dashboard

Your home page: active project count, releases needing attention,
deadlines in the next 14 days, unconfirmed rights, active projects by
stage, recent asset versions, open scanner findings, open marketing
drafts, recent analytics imports, and backup status -- each with a link
to the relevant page.

## Artists & Projects

**Artists** (`/artists`) are just a name -- attach projects to one, or
leave a project unassigned.

**Projects** (`/projects`) are the central entity. Creating one asks for
a working title, artist, genre, BPM, and key; everything else (final
title, full musical metadata, FL project paths, rights summary,
distributor/ISRC/UPC, tags) is edited on the project detail page.

**Workflow state**: every project has a stage -- `Idea`, `Arrangement`,
`Production`, `Vocals`, `Editing`, `Mix`, `Master`, `Release Ready`,
`Scheduled`, `Released`, `On Hold` -- changed from a dropdown on the
project page. Every change is logged (visible in the audit trail).

**Tracks**: a project can have more than one track (e.g. an EP) --
add them from the Tracks section of the project page.

## Assets & versions

Under a project's **Assets** section, register a file by pointing at its
path (e.g. `D:\Music\Exports\Track_Master_v1.wav`) and choosing an asset
type (Master, Mix, Stems, Artwork, etc.). ProducerOS **never touches the
file itself** -- it only records metadata about it (path, type,
version). Registering a new version of an existing asset type keeps the
version history; mark whichever one is current.

## The scanner

`/scanner`: point ProducerOS at one or more folders (e.g.
`D:\Music\Projects`) and run a scan. It's **read-only** -- it never
deletes, renames, moves, or uploads anything. A scan reports new files,
new versions of things you've already registered, duplicates (by content
hash), missing files, unexpected file types, and locked/unreadable files.
Approve a finding to register it as an asset version, or dismiss it.

## Rights & clearances

On a project's **Rights** section: add contributors (name, role, email),
mark them approved; add rights shares (holder, type, percentage) --
ProducerOS validates that shares of each type sum to 100% and shows a
warning if they don't, but **never auto-corrects a percentage**; and
track sample/interpolation clearances through to resolution.

## Releases & readiness checklist

Start a release from a project (`/releases/new?project_id=...` or the
"Start a release" button on the project page). ProducerOS immediately
runs a deterministic ~30-rule readiness checklist across audio,
metadata, rights, and marketing categories -- no AI judgment calls, just
concrete checks (e.g. "master registered," "rights shares confirmed,"
"ISRC set"). Re-run the checklist any time from the release page as you
fix issues; individual results can be waived with a reason if a rule
genuinely doesn't apply.

## Marketing

`/marketing`: create a campaign, attach content assets (photos, videos,
etc.), and generate marketing drafts (captions, bios, pitch notes) from
16 local, deterministic templates -- **no AI**, and no invented facts,
streaming numbers, or press mentions. Every generated draft is editable
before you use it anywhere.

## Calendar

`/calendar`: deadlines (release dates, marketing beats, delivery
due-dates) with a 90-day upcoming view and an overdue list. Export the
whole calendar as a standard `.ics` file for your phone/desktop calendar
app via the Export link.

## Delivery packages

`/delivery`: pick a project and a preset (client, sync licensing, or
distributor), then generate a manifest -- a **dry-run** listing of every
file that would be copied and where, with checksums. Review it, approve
it, then execute it. Execution refuses to overwrite an existing output
directory, so re-running a delivery never silently clobbers a prior one.

## Analytics

`/analytics`: import streaming/sales CSVs (there's no platform API
integration -- you export a CSV from wherever you track this and import
it here) to get summaries per project/period.

## Backups

`/backup`: create a backup any time, verify its integrity, and restore
from one if needed (a pre-restore safety copy is always taken
automatically first). Full walkthrough: `docs/BACKUP_RESTORE.md`.

## Search

The search box (or `/search`) looks across projects, artists, and
releases at once.

## Phone access

See `docs/ANDROID_PWA.md` for pairing a phone over your LAN and
installing ProducerOS as a home-screen app.

## Further reading

- `docs/ADMIN_GUIDE.md` -- operational tasks (backup scheduling,
  scanner roots, LAN devices, settings).
- `docs/RELEASE_PROCESS.md` -- the recommended end-to-end release
  workflow.
- `docs/MCP.md` -- optional AI-assistant integration.
- `docs/TROUBLESHOOTING.md` -- common problems.
