# Producer showcase and music connections

Assessed 2026-09-10. The owner subsequently authorized the first curated-link
stage and requested generated rap/trap examples until real producer clips are
available. See [the showcase workflow](SHOWCASE_WORKFLOW.md) for that implementation
and [the launch record](WEBSITE_LAUNCH.md) for verification/publication status.
Accounts, public website comments, uploads and authenticated music-service
connections remain proposals; their later stages are not authorized to launch.

## Recommendation

Start with a small, curated showcase built around **links to clips published
by their producers**. Each entry has a producer name, title, genre/BPM if
supplied, a short description and one specific feedback question. Use official
embeds selectively after checking their permitted use. Add website comments
only when the first producers return and give useful feedback. Delay direct
uploads and authenticated platform connectors.

The useful proposition is feedback that helps a producer finish a track. A
generic beat feed competes with established music platforms and gives people
little reason to return. A sensible first experiment is 5–10 invited producers,
one 30–60 second clip each, reviewed over two weeks. These are proposed trial
limits, not observed demand. Assess repeat participation and whether feedback
led to a revision; visits and upload counts alone do not validate a community.

| Rank | Stage | What it needs | Main trade-off |
| --- | --- | --- | --- |
| 1 | Curated links, selective official embeds | Producer consent; manual review of submitted public URLs; small static cards | Lowest maintenance; listening/comments may happen on the external platform |
| 2 | Website feedback below approved entries | Separate website accounts, database, moderation queue and reporting | Comments stay together on prodos.tech; the owner must operate moderation |
| 3 | Limited public clip uploads | Stage 2 plus object storage, secure validation, quotas and a publication/takedown policy | Consistent playback and provider independence; substantially more responsibility |
| 4 | Authenticated music-service connectors | A concrete need, eligibility approval, OAuth, server-side secrets, revocation and quota handling | Helpful for specific workflows, but adds little to a first showcase |

## Platform findings

**SoundCloud — use links first.** Its standard sharing controls can generate
an official embedded player without registering a custom API app. The uploader
controls sharing/app-playback settings; hiding the embed code does not revoke
players already embedded. However, its widget terms restrict aggregating
SoundCloud content into a separate content service and artist/genre destinations.
Do not assume a SoundCloud-powered beat feed is permitted merely because embeds
work. Get scope-specific provider clearance before relying on it as the
community's listening layer. [Embedding guide](https://help.soundcloud.com/hc/articles/115003453587-Embedded-players),
[permissions FAQ](https://help.soundcloud.com/hc/en-us/articles/31423752369691-Displaying-An-Embed-Code-For-Your-Track),
[player/widget terms](https://soundcloud.com/terms-of-use).

Custom API registration now requires **Artist Pro**. The published web price is
**US$99/year ($8.25/month equivalent, billed annually)**; local taxes, territory
and checkout price are unverified. Basic hosting lists two hours of uploads.
API access itself is described as free, but that does not waive the subscription
requirement or use restrictions. The API's stream endpoint allows **15,000 play
requests per client ID per 24-hour window**; client-credential issuance has
separate limits (50/12 hours/app; 30/hour/IP). These API quotas are not promises
about widget capacity. [Registration](https://developers.soundcloud.com/docs/api/register-app),
[pricing](https://soundcloud.com/getstarted/pricing),
[API limits](https://developers.soundcloud.com/docs/api/rate-limits).

SoundCloud API terms restrict aggregation, caching/offline downloads and
commercial uses. A community must not funnel multiple producers' content into
one shared SoundCloud account; authenticated actions must be deliberately
initiated by each user. An API connector would need a separate permitted-use
review. [API terms](https://developers.soundcloud.com/docs/api/terms-of-use).

**Bandcamp — useful for producer-owned releases.** Official Share/Embed players
are documented; exclusive/pre-release embeds have separate permission settings.
Use the player intact and retain the link to the artist's page. No custom API
credential is needed for this standard embed flow; the docs do not publish a
per-play price or numeric embed quota. Its account API is for labels and merch
fulfilment partners, with requested access and OAuth. Public approval criteria
for a general producer-community connector, pricing and numeric API quotas are
not established by that documentation. Do not scrape or promise a universal
Bandcamp connector. [Embed guide](https://get.bandcamp.help/en/articles/15263071-how-do-i-create-a-bandcamp-embedded-player),
[exclusive embeds](https://get.bandcamp.help/en/articles/15263063-how-do-i-set-up-an-exclusive-embed),
[API access](https://bandcamp.com/developer).

**Spotify — link/embed released music; avoid its API as a launch dependency.**
Its official embed flow supports tracks, albums and playlists without custom
Web API OAuth. Playback can be restricted to a short preview depending on the
browser/player conditions; it is not an upload service for unreleased beats.
No standalone embed price or numeric embed quota is published in these guides.
[Embed guide](https://developer.spotify.com/documentation/embeds/tutorials/creating-an-embed),
[playback limitations](https://developer.spotify.com/documentation/embeds/tutorials/troubleshooting).

New development-mode API apps require a Premium owner and allow five
authenticated users. Wider access applications currently require an established
organization, launched service and at least **250,000 monthly active users**,
among other criteria. The July 2026 update raised the developer app allowance
to 25; older February references to one app are stale. Quotas are shared per
developer account, and burst limits use a rolling 30-second window without a
universal published numeric allowance. There is no verified pay-to-remove-limit
option here; the owner's local Premium price was not checked.
[Quota eligibility](https://developer.spotify.com/documentation/web-api/concepts/quota-modes),
[July update](https://developer.spotify.com/blog/2026-07-23-web-api-quota-updates),
[rate limits](https://developer.spotify.com/documentation/web-api/concepts/rate-limits).

**YouTube — optional for producers already publishing videos.** Use the
official visible player, keep its controls/branding and required referrer
identification, and respect disabled embedding (errors 101/150). Do not extract
audio or make a hidden audio player. Basic embeds do not need the Data API;
if catalog/search/upload APIs are later needed, the current default allocation
lists 100 search calls, 100 video uploads and 10,000 units/day for other
endpoints, with a compliance process for more quota. No per-play embed tariff
is documented in these sources; ads/platform conditions still apply.
[Player reference](https://developers.google.com/youtube/iframe_api_reference),
[required functionality](https://developers.google.com/youtube/terms/required-minimum-functionality),
[current API allocation](https://developers.google.com/youtube/v3/getting-started).

All external players add third-party requests and platform availability/privacy
dependencies to the website. A future implementation should use a clear
click-to-load player, an outbound-link fallback and narrowly scoped CSP changes.
The current site's self-only CSP intentionally does not permit these embeds.
Accept allowlisted URLs/IDs, never arbitrary user HTML or arbitrary server URL
fetches. None of this belongs in the offline desktop runtime.

## Hosting and cost

The live site dashboard confirms **Business Web Hosting with a 50 GB plan
limit**. That is shared plan capacity, not an allocation reserved for a music
community. Existing plan limits take precedence over current sales pages.
The plan is appropriate for the current static site and a small curated
showcase. A light PHP/database comments service is plausible, but has not been
built or load-tested. It is not the Windows/Python desktop app running remotely.
[Hostinger limits](https://www.hostinger.com/support/6976044-parameters-and-limits-of-hosting-plans-in-hostinger/).

Hostinger explicitly supports embedded multimedia on its plans, while the
detailed streaming section says audio/video streaming is supported on VPS.
That article's introductory wording is inconsistent, so do not treat shared
Business hosting as approval for an audio-streaming service. Confirm the exact
model with Hostinger before serving user-uploaded audio there. Existing demo
playback is not proof that a community music-hosting workload is supported.
[Server capabilities](https://www.hostinger.com/support/which-server-capabilities-are-supported-at-hostinger/).

| Option | Storage/bandwidth responsibility | Planning cost and limits |
| --- | --- | --- |
| External links/official players | Producer's platform stores/transcodes/serves audio | Approximately $0 additional ProdOS infrastructure for the static pilot; producer plan costs and owner review time remain |
| User clips on shared web hosting | ProdOS and the shared hosting account | No new plan charge assumed, but unsuitable as the default: finite shared disk/I/O and unresolved streaming support |
| Separate object storage | ProdOS controls clip admission and publication; storage provider serves bytes | Usage billing plus application/moderation work; suitable later with enforced quotas |

**Object-storage example, not a purchase recommendation yet:** Cloudflare R2
Standard includes 10 GB-month, 1 million Class A operations and 10 million
Class B operations/month. Above those, published rates are $0.015/GB-month,
$4.50/million A and $0.36/million B; direct R2 egress is free. It requires an
account and R2 subscription, and related compute/email services can cost extra.
Free allowances are account-level, not guaranteed unused for ProdOS.
[R2 pricing](https://developers.cloudflare.com/r2/pricing/),
[subscription setup](https://developers.cloudflare.com/r2/get-started/).

At a proposed 4 MB cap, 100 producers × 5 clips = **2 GB** before artwork,
pending uploads and backups. Ten thousand complete 4 MB plays transfer about
**40 GB**. At 100 GB stored all month, R2 storage is about **$1.35/month** after
an unused 10 GB allowance, plus operations/other services/taxes. These are
arithmetic estimates, not a measured monthly bill or a total operating budget.
Request abuse, development and human moderation can dominate the storage cost.

## Minimum for a later community

- **Accounts:** separate from desktop login; verified email or an approved
  identity provider, account recovery, secure sessions, rate limits and an
  administrator with stronger authentication. Verify transactional delivery
  before depending on email; the contact mailto link proves none of this.
- **Feedback:** plain text, maximum 1,000 characters, no attachments/links at
  first, e.g. 10 comments/day and one/minute/account. Review new users' comments
  before publication; provide reporting, blocking, an audit trail and a named
  human moderator. No anonymous comment box, direct messages or automated
  promotional comments in the first version.
- **Clips:** proposed MP3-only, 30–60 seconds, maximum 4 MB, five active clips
  per producer, invite-only initial admission. Check actual decoded format,
  duration and size server-side; file extensions and browser checks are
  insufficient. Reject archives, project files, WAV stems and executable content.
  Keep new objects private pending checks; use new unique object names and
  never overwrite a music file. Serve validated media from a separate origin.
  [OWASP upload guidance](https://owasp.org/www-community/vulnerabilities/Unrestricted_File_Upload).
- **Quotas and operations:** count pending/failed uploads too; enforce per-user
  and whole-site storage limits before accepting bytes. Set request budgets,
  traffic alerts and a pause mechanism; billing alerts alone are not hard caps.
  Back up metadata and test restoration. Specify retention and who handles
  incident reports before launch. A reliable validation/transcoding worker is
  extra infrastructure; do not assume shared hosting can run arbitrary binaries.
- **Rights:** contributors retain ownership and explicitly authorize public
  playback of that exact clip, artwork and description. Obtain permission for
  collaborators/samples; short or free previews do not establish clearance.
  Default to listening, not sample reuse/licensing/download permission. Explain
  that playable public audio can be captured. Provide a complaint/takedown and
  appeal process, privacy notice and a jurisdiction-specific launch review.
  Bandcamp likewise requires rights even for free uploads.
  [Bandcamp rights terms](https://bandcamp.com/terms_of_use).
- **Safety boundary:** the website never accesses local folders, reuses desktop
  credentials or publishes a project automatically. The owner's prohibition on
  deleting or overwriting user/music files also constrains uploaded copies.
  Unpublishing can revoke public access without deleting the underlying audio;
  retained objects must still count against storage quotas. A lifecycle that
  requires file deletion is incompatible with this rule, even with approval.
  Resolve that constraint before accepting uploads; otherwise retain external
  links. No hosted policy may modify a producer's original files.

The main launch blockers are platform permission, repeat producer participation
and ownership of moderation. APIs and cheap disk do not solve those problems.
No paid service, account, connector or upload facility was created as part of
this assessment. The later curated showcase uses static listings and manual
email intake; generated examples are clearly distinguished from real submissions.
