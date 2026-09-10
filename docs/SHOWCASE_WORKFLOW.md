# Curated producer showcase

The first stage is a static public page at `https://prodos.tech/showcase.html`.
It is separate from the offline desktop app. There are no website accounts,
uploads, embedded external players, APIs or public comment database.

The owner authorized the first stage on 2026-09-10, then requested generated
rap/trap examples under fictional artist names until real clips are available.
The three examples are explicitly labelled **generated demo / fictional artist**:

| Fictional artist | Demo | Style | BPM | Length |
| --- | --- | --- | --- | --- |
| Hoodie Monstah | Night Shift | Dark trap | 140 | About 34 seconds |
| Deid Gravic | Side Street | Laid-back rap | 92 | About 42 seconds |
| Lowkey Circuit | Blue Hour | Melodic trap | 128 | About 38 seconds |

`scripts/generate_showcase_audio.py` synthesizes every voice using oscillators
and seeded noise, with no recordings, samples, APIs or third-party runtime
dependencies. The builder creates mono 16-bit 22,050 Hz WAVs. These are demo
instrumentals, not claims of real artists, demand, testimonials or finished
commercial releases. Do not silently convert them into producer submissions.
The generator creates new audio exclusively, reuses identical generated files
and refuses an existing file whose content differs. To change a composition,
use a new track ID/filename; do not replace or delete an older audio file.

## Intake and review

1. The visitor chooses **Email your clip link**. This opens a local mail draft
   addressed to `contact@prodos.tech`; the visitor reviews and sends it.
   The page also provides the address and a readable brief if no mail app opens.
   No email is sent automatically. Mailbox delivery has not been tested here.
2. Review the producer name, title, direct public 30–60 second clip URL and
   specific feedback question. Genre/BPM are optional; omit unknowns.
3. Verify that the submitter explicitly permits the listing and confirms the
   necessary music/collaborator permissions. A public URL alone is not consent.
   Open the link manually, check its content/duration and remove tracking
   parameters. Do not download private project files or fetch arbitrary URLs
   in server code. API/embed permission is not implied by listing a link.
4. Keep correspondence and consent evidence in the owner's private workflow,
   outside this public repository and deploy bundle. Do not put email addresses,
   private URLs/tokens, attachments or pending submissions into the catalog.
5. Add only the approved public metadata to `website/showcase.json` and rebuild.
   Review the exact rendered entry before publishing. A later producer's consent
   does not authorize messaging them or publishing unrelated content.

The initial catalog is empty. The build refuses unapproved entries, unknown
fields, unsafe/unrecognized URL patterns, duplicate IDs, multiple clips by the
same producer and more than ten entries. It escapes all submitted text. These
checks do not independently prove consent, ownership or the remote clip's
contents; human review remains required.

Use this shape when an actual entry is approved (the example below deliberately
cannot build until reviewed; never publish this fictional external URL):

```json
{
  "entries": [{
    "id": "producer-track",
    "producer": "Approved public producer name",
    "title": "Approved track title",
    "url": "https://soundcloud.com/producer/track",
    "feedback_question": "The producer's specific question",
    "duration_seconds": 45,
    "genre": "Supplied genre",
    "bpm": 140,
    "producer_permission_confirmed": false,
    "publication_approved": false
  }]
}
```

Supported link shapes: SoundCloud artist/track, Bandcamp artist subdomain/track,
Spotify track and YouTube watch/short video URLs. Use HTTPS with no credentials,
custom port, private token or tracking parameters. Only YouTube's `v` query
parameter is accepted. Custom artist domains and shortened/tracking links must
be reviewed and converted to a supported direct URL, not added to the allowlist
casually. External content can change after review; periodically check listings.

## Feedback, corrections and the first experiment

Visitors can comment on the original platform where enabled. Each real listing
also offers a manual feedback email draft identifying the listing and asking
whether the feedback may be shared with the producer. Do not forward it without
permission. The public correction/report link opens a separate manual draft.

For a correction or unlisting, review the request and edit/remove the public
metadata entry, rebuild and publish the page. This never deletes or modifies
music on the external platform or the producer's PC. Public source history may
retain old listing metadata; never commit confidential information to begin with.
Keep unpublishable/pending submissions out of the public catalog.

Aim for 5–10 consenting producers and a two-week listening experiment beginning
when that group is actually assembled. No participants have been recruited and
no invitations were sent by this change. Manually record participation and
whether specific feedback led to a revision; there are no analytics or timers.
Repeat engagement is a prerequisite for considering website comments/accounts.
See [the assessment](COMMUNITY_FEASIBILITY.md) for those later stages.

## Build and publish

Use the existing [website build instructions](../website/README.md). The builder
includes `showcase.html`, `showcase.css`, `showcase.js` and three generated audio
files in its explicit public allowlist. The catalog, scripts and private intake
are not deployed. The sitemap includes the new page. Existing CSP rules suffice:
all loaded assets are local, and external music links load only when clicked.

For this first launch, publish only the built homepage, showcase HTML/CSS/JS,
sitemap and the three `assets/showcase/*.wav` files to the existing outer
Hostinger `public_html`. Preserve other files and the reviewed Windows download.
The Windows app stays at 0.2.1; no desktop source, binary or data migration changes.

Run `python -m pytest tests/website -q` after building. Website-only environments
can add `--confcutdir=tests/website` to avoid loading desktop fixtures. Install the
repository's declared Playwright Chromium first. Tests cover real local audio
playback/seek/pause, safe catalog rendering and rejection, intake drafts,
no-JavaScript use, responsive layouts and the original app download/demo.

Browser playback checks and signal-level checks do not establish owner musical
acceptance, mailbox delivery, physical-phone compatibility or production load.
