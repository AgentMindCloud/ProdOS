# Recommended Release Process

A suggested end-to-end workflow through ProducerOS's features, from an
idea to a delivered release. None of this is enforced rigidly -- the
readiness checklist is advisory, not a hard gate -- but it maps to how the
app's pieces are meant to fit together.

## 1. Create the project

`/projects/new` -- working title, artist, genre, BPM, key. Move it
through workflow states (`Idea` -> `Arrangement` -> `Production` -> ...)
as it progresses; each change is logged.

## 2. Register assets as you produce

As you export mixes/masters from FL Studio, register each one under the
project's **Assets** section (file path + type). Either register them
manually, or point the **scanner** at your export folder and approve the
findings it reports -- either way, ProducerOS only records metadata, it
never touches the files.

## 3. Lock down rights

Add every **contributor** and get them marked approved. Add **rights
shares** for each share type (composition, master, etc.) and confirm
each one once percentages are agreed -- ProducerOS warns if a type
doesn't sum to 100% but never silently corrects a number for you. Resolve
any sample/interpolation **clearances**.

## 4. Start a release and check readiness

From the project page, **Start a release**. ProducerOS immediately runs
the ~30-rule readiness checklist (audio, metadata, rights, marketing
categories). Work through anything flagged, re-running the checklist as
you go (`/releases/{id}` -> re-evaluate). If a rule genuinely doesn't
apply to this release, waive it with a reason rather than ignoring it
silently -- the waive is recorded, not hidden.

## 5. Build marketing material

Generate drafts (captions, bio snippets, pitch notes) from the local
templates under `/marketing`, attach content assets (photos/videos), and
edit every draft before using it -- the templates never invent facts,
numbers, or credits, so anything specific (features, awards, streaming
counts) is up to you to add truthfully.

## 6. Schedule it

Add deadlines on `/calendar` for the release date and any marketing
beats/delivery due-dates. Export to `.ics` to get them into your regular
calendar app.

## 7. Package the delivery

`/delivery` -- pick the project and the right preset for who's receiving
it (client, sync licensing, distributor). Generate the manifest (a
dry-run listing with checksums), review it, approve it, then execute.
Execution refuses to overwrite an existing output folder, so re-running
a delivery is always safe.

## 8. Back up

Take a backup (`docs/BACKUP_RESTORE.md`) once the release ships, so this
release's full metadata state is preserved independently of your live
working database.

## 9. Track results

Import streaming/sales CSVs on `/analytics` as they become available to
keep a record against the project, without any platform API integration.
