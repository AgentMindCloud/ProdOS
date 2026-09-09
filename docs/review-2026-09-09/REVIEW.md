# ProducerOS review and redesign

Reviewed on 9 September 2026, before website and GitHub publication. The report
below preserves that review's scope and evidence. For subsequent publication
status, see [the current handoff](../../HANDOFF.md) and
[website launch evidence](../WEBSITE_LAUNCH.md).

## Recommendation

Keep ProducerOS on your friend's Windows computer. Use a public website for the product story, documentation and downloads if you later choose to publish it. This preserves the strongest existing feature: managing a real music folder without uploading or duplicating the collection.

The app has a useful working foundation: projects, assets and versions, rights validation, release checklists, calendar, deterministic marketing drafts, read-only scanning, approved delivery/file operations, CSV analytics, metadata backups and optional local MCP. It is suitable for a supervised friend trial. Passing the checks below does not establish that every workflow, large library or public deployment is production-ready.

## What changed

- Replaced the dark interface with the supplied reference's pale blue glass panels, cyan controls, colorful stage badges, iridescent cover illustration and clearer spacing. Reworked the dashboard, project library and project detail; applied the theme to the remaining routes.
- Kept the actual existing forms and workflows. The project section controls navigate to Overview, Assets, Rights and Tracks; they are functional section links.
- Added authenticated previews of registered local audio and artwork. The dashboard and project detail can play the current master/mix, pause, seek and skip ten seconds. Native audio controls remain available without JavaScript. Browser codec support varies; no transcoder was added.
- Added a live frequency visualization during playback. It is derived from the playing audio; it is not a precomputed track waveform. The bundled disc image is a decorative placeholder, not generated artwork for the producer's track. Registered artwork is used in the project/featured hero; library thumbnails use the default illustration with stage colors.
- Improved small-screen layout, visible asset tables, filter keyboard handling and no-JavaScript filters. All new fonts, graphics, CSS and scripts are local assets. The original Content Security Policy remains strict.

### Defects fixed

| Problem | Corrected behavior / evidence |
|---|---|
| Editing a project could clear its tags because the form did not load them | Tags are loaded and preserved; integration and browser regression tests |
| Unchecking “Splits confirmed” did not clear confirmation | Explicit full-form checkbox presence is handled; partial edits preserve existing state |
| Missing or malformed project IDs could become server errors | Project lookup returns 404; browser requests receive a useful error page |
| Dashboard totals were capped by short preview lists | Separate full counts; tested with twelve records |
| Two backups within the same timestamp could overwrite the same destination | Unique backup and pre-restore snapshot names |
| A valid but unrelated/empty SQLite file could pass restore preflight | Required tables/columns are checked before restore; incompatible snapshots are rejected |
| Restore dry-run UI and analytics filtering relied on inline JS blocked by the app's own CSP | External JavaScript/progressive forms; real browser checks |
| Analytics import had no effective total request/row bound and accepted invalid numeric data | Request bounded before multipart parsing; 5 MiB CSV / 10,000 rows; invalid dates, projects and nonfinite numbers rejected |
| Configured scanner file-size limit was ignored | Oversized files are reported without hashing/reading their content; regression asserts no hash call |
| Offline retry remained on the offline page; cached summary rendering used HTML | Retry returns to the app; cached summary is structured text and cleared at sign-out/login |
| Generic table hiding on mobile also hid asset versions | Only the project table with duplicate mobile cards is hidden; asset tables remain accessible |
| Login's return destination accepted a network-path URL | Redirects stay within the app; external/ambiguous destinations are rejected |

Tests that reproduced the tag/checkbox and login defects failed before the corresponding fixes. No real music files were modified during the review. Test media and databases were isolated synthetic fixtures.

## Storage and Hostinger

**The main capacity issue is disk space, not simply RAM.** A four-minute stereo 24-bit / 48 kHz WAV is approximately 69.1 MB before headers (`240 × 48,000 × 2 × 3`). A thousand such files are about 69 GB; alternate mixes, stems and backups multiply that. This is an illustrative calculation, not a workload benchmark.

The current app has no music-upload endpoint. It records local paths, metadata and hashes. Its only browser file upload is analytics CSV, now bounded. Audio previews stream byte ranges from approved local folders, with `preload="none"` and no audio caching in the service worker. A security test verifies bounded file reads of at most 64 KiB for streaming; this does not imply that total process memory is only 64 KiB.

| Option | Assessment |
|---|---|
| Local Windows app + Hostinger website/downloads | **Recommended.** Music and SQLite metadata stay on each producer's computer; no per-user music storage on Hostinger |
| This Python app on a Hostinger VPS | Technically a possible server runtime, but changes the product's operating model. A server path cannot locate files on the visitor's PC. Current single-user/LAN security is not a public SaaS design |
| Pure browser app with local folder permissions | Possible separate redesign, with permission persistence, browser compatibility, local database and backup/recovery work. Not a simple deployment of the existing Python scanner |
| Cloud music storage / collaboration service | Requires explicit scope change, tenant isolation, quotas, cost controls, auth/recovery, background processing and public-service operations. Not implemented |

Hostinger currently documents Python support on self-managed **VPS**, rather than standard Web/Cloud hosting. Its KVM 1 listing advertises 4 GB RAM and 50 GB NVMe storage; that storage is not a music-library quota or a capacity guarantee for this app. [Supported languages](https://www.hostinger.com/support/which-programming-languages-and-frameworks-are-supported-at-hostinger/), [VPS plans](https://www.hostinger.com/vps-hosting).

Hostinger's free-domain offer includes `.tech` for eligible KVM plans, normally with a new plan billed for at least twelve months. It covers **one year**, followed by paid renewal. Availability of `prodos.tech`, your account's entitlement, checkout price and renewal amount were not verified. Do not buy a server just to obtain the domain. [Free-domain terms](https://www.hostinger.com/support/1583407-how-to-register-a-domain-for-free-at-hostinger/).

Your friend's country does not prevent local use. Phone access requires the producer's computer running and the existing local-network setup; cross-country remote access is not provided. Never expose the local app by forwarding its port through a router.

Local storage still needs care: metadata snapshots accumulate, logs and scanner findings grow, and an approved delivery bundle can duplicate selected audio locally. ProducerOS backups contain metadata **only**, not music. The producer should keep a separate backup of music folders and explicitly manage old snapshots/bundles. Moving the app's metadata to a second PC does not relink different drive paths automatically.

## What should be built next

These are priorities, not features claimed to have been delivered.

1. **Friend handover:** test the updated Windows build on his actual computer; document install/upgrade and folder setup. Add a friendly folder picker and local password change/recovery. Back up existing metadata before upgrading.
2. **Recovery and disk visibility:** show storage usage, add a carefully approved backup-retention policy and a moved-file relinking workflow. Preserve dry-run approval for music operations.
3. **Large libraries:** background scan jobs with progress/cancel, pagination and repeatable performance tests using representative file counts and sizes. The scanner currently runs synchronously; enforcing its per-file size limit does not bound an entire scan's runtime or findings count.
4. **Finish/release workflow:** A/B listening, full waveform overview, richer multi-track delivery/checklist handling and local analytics charts. Prove that these save time before broadening the product.
5. **Release operations:** rebuild/test the installer, code signing, clean-machine/upgrade tests and restore the Linux browser suite as a release gate. Existing release workflow disables e2e because of an older reported Ubuntu fixture issue; this review's Windows success does not resolve that issue.

Do not prioritize billing, cloud sync or AI integrations before those workflow and adoption questions are answered. Existing offline, no-publishing and deterministic-marketing constraints remain in force.

## Monetization assessment

**There is a plausible small paid-desktop/support opportunity, but willingness to pay is unproven.** The strongest position is a private FL Studio companion that organizes versions, rights and release readiness without moving unreleased audio. It is a weaker proposition as a generic music-project dashboard or another cloud-storage subscription.

Competition is substantial: Session Studio advertises a free tier with unlimited song projects, credits/splits tools and 2 GB storage, plus a paid Creator tier. Notetracks markets audio playback and detailed feedback/collaboration. These are vendor feature/pricing claims, not evidence that buyers prefer them or that ProducerOS has demand. [Session Studio pricing](https://www.sessionstudio.com/pricing), [Notetracks pricing and features](https://pro.notetracks.com/pricing).

An initial **$29–59 one-time price is a test hypothesis**, not a valuation or established market price. Charge for a convenient supported Windows build, onboarding and useful workflow templates; scope support carefully so a low price does not buy unlimited custom help. The repository is MIT-licensed: do not base the business on source exclusivity or add an online licence dependency to this offline product.

Before paid development, ask five to ten independent producers to use it through an actual project/release. Record repeated weekly use, errors, setup friction and specific time saved; seek a concrete paid pilot after the trial. One happy friend is useful product feedback, not market validation. No outreach, payments, publication or licensing change was performed.

## Verification actually performed

- Windows / Python 3.12.14: **161 backend tests passed, 3 skipped**; **6 Chromium browser tests passed**. The three skips were two unavailable Windows symlink tests and one filesystem-permission simulation unavailable under this account. One Starlette/httpx test-client deprecation warning remains.
- Ruff lint and formatting passed; mypy passed over 89 source files. JavaScript syntax checks passed. A fresh database migrated cleanly; Alembic reported no schema drift; synthetic demo load/clean completed.
- Actual browser review of desktop dashboard, project list and project detail, plus a 390-pixel phone viewport. Separate automated browser checks exercise mobile asset access, no-JavaScript filters, play/pause/seek state, backup dry run, analytics filters and offline recovery.
- Built an actual Windows PyInstaller executable. Its health endpoint reported 0.2.0; setup/login, 21 page/static endpoints, project creation, backup dry run, external-redirect blocking and graceful shutdown passed using an isolated data directory. See [packaged smoke results](package-smoke.json).
- An independent verifier checked the media, import and backup changes, and identified the CSP-blocked backup control subsequently fixed and exercised in Chromium.

**Not verified:** a clean Windows machine without development tools; a newly compiled Inno installer, interactive upgrade/uninstall or SmartScreen behavior; a physical Android/iOS device; every supported audio codec; hostile symlink races; heavy concurrent/large-library workloads; updated GitHub Actions; external MCP-client behavior; any Hostinger deployment or account/domain entitlement. No claim of “everything is bug-free” is made.

## Handover files

- [Windows portable instructions](WINDOWS_PORTABLE.txt) and local artifact: `release-artifacts/ProducerOS-0.2.0-Windows.zip` at repository root. Extract the entire folder and run `ProducerOS.exe`; retain `_internal`. The application uses the usual separate user data directory by default.
- The existing `installer/ProducerOS-Setup-0.1.0.exe` is unchanged and contains the old UI. The 0.2.0 ZIP is a portable build, not a rebuilt installer or a published GitHub release.
- [Desktop dashboard](02-dashboard-after.png), [project library](03-projects-after.png), [project detail](04-project-detail-after.png), [phone dashboard](05-mobile-dashboard.png), [original dashboard](01-dashboard-before.png). All depicted project data/audio are synthetic.
- [Build environment](build-environment.txt) records installed tool/library versions. Source setup still uses the repository's declared dependency ranges; the pre-existing `requirements.lock` was not regenerated in this review.

This workspace was a downloaded snapshot without `.git`. Changes are local; no commit, push, domain registration or deployment occurred.
