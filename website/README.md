# ProducerOS public companion website

This is a separate, static product website for `https://prodos.tech`.
It does not expose or modify the Python desktop app. HTML, CSS, JavaScript,
images and an original synthesized demo loop are served as ordinary files.
The interactive sample projects stay in browser memory and reset on reload.

## Build

From the repository root, prepare the reviewed Windows preview package at
`release-artifacts/ProducerOS-0.2.1-Windows.zip`. Keep the complete portable
app folder in the ZIP, including `_internal`. A future GitHub release is not
assumed to exist, and the website deploy archive is not a GitHub release asset.

The 0.2.1 binary passed an isolated Windows package smoke check. Its exact
SHA-256 is pinned in `scripts/build_website.py`; never reuse an old version's
hash or silently change a reviewed archive. The builder refuses unknown hashes.

Then build the site (the builder verifies the pinned binary hash):

```powershell
.venv/Scripts/python.exe scripts/build_website.py
```

Output: `.work/website-dist/`, with `index.html` at its root.
Deploy archive: `release-artifacts/prodos-site-20260910.zip`.
The sidecar manifest records every public file and checksum.

The builder copies only the three website source files, designated local
graphics, generated sample audio, the reviewed Windows package, its setup
guide/license/checksum, release metadata and hosting configuration. It never
copies the repository, app database, private configuration, accounts or a
producer's audio folder. Unrecognized Windows ZIP hashes fail the build.

The reviewed 0.2.1 app package is a build artifact, not a runtime dependency
for the desktop app. To produce a new version from source, run
`scripts/build_windows.ps1`, package the whole `dist/ProducerOS/` folder,
verify it on Windows and update the reviewed release version/hash in the
website builder and page together. Do not silently substitute a different
binary under a reviewed download name.

The builder copies the setup guide from
`docs/review-2026-09-10/WINDOWS_PORTABLE.txt`. It calculates the displayed
download size from the actual reviewed ZIP and replaces the single
`{{APP_DOWNLOAD_SIZE}}` placeholder in `website/index.html`. Serve the built
output, not the unrendered source. Release metadata records the exact byte
count, SHA-256 and release date (2026-09-10).

The 0.2.1 release notes focus on file safety: no delete/overwrite operations,
approved moves/renames, exports into new folders and retained demo files.

## Local preview and tests

```powershell
.venv/Scripts/python.exe scripts/preview_website.py
.venv/Scripts/python.exe -m pytest tests/website -q
```

Install the repository's Playwright Chromium runtime if it is not available.
The browser tests use an isolated static HTTP server with the intended CSP
and byte-range support for audio seeking. They do not start or connect to the
desktop backend. The local preview mirrors these headers but does not interpret
`.htaccess`; live header behavior needs a separate HTTPS check after deployment.

## Hosting

Use the existing Hostinger Business Web Hosting site's `public_html` for
`prodos.tech`. Upload/extract the build archive so `index.html`, `site.css`,
`site.js`, `.htaccess`, `assets/` and `downloads/` are directly in that folder.
No PHP application, Node server, Python process, database, API key or plugin
is required. The desktop app stays on the visitor's PC.

The `.htaccess` file sets `DirectoryIndex index.html`, so Hostinger's original
`default.php` can remain as a rollback fallback. Review existing site files
before any later deploy; do not overwrite a different site's content.

After upload, verify HTTPS without bypassing certificate errors, the exact
page headline, demo interactions, mobile layout and the full Windows download
SHA-256. Confirm server headers instead of assuming `.htaccess` was applied.

No app-to-website background connection, tracking, newsletter service,
account system, payment or file-upload feature is implemented. Feedback uses
a user-initiated link to the public GitHub Issues page. Hostinger may retain
normal server access logs; the page does not add analytics scripts.

Public release is an explicit final operation after the user reviews the
site and exact archive. See `docs/WEBSITE_LAUNCH.md` for the current evidence.
