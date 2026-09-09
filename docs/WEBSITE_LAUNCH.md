# prodos.tech launch verification

Date: 2026-09-09. This file records the public companion site separately from
the earlier desktop app review. No account credentials or registrant contact
details belong here or in the deployment archive.

## Hostinger observations

Read directly from the user-opened hPanel session:

- `prodos.tech` is active. Domain overview initially reported SSL installation
  in progress; HTTPS was subsequently verified in the browser.
- The site uses an existing Business Web Hosting plan. Account billing dates,
  other website counts and account-wide resource usage are not public release data.
- A PHP/HTML website entry for `prodos.tech` is present. Before publication,
  its site-specific File Manager showed only `public_html/default.php`.
- hPanel initially reported domain connection in progress. A subsequent real
  browser visit to `https://prodos.tech/` passed the host's browser check and
  reached its default "You Are All Set to Go!" page without a certificate bypass.
  A direct HTTP client receives the host's browser-check challenge (403), so
  live file verification therefore used the normal browser download flow.
- The public GitHub repository and its Issues page are accessible. No issue
  was submitted. After the website launch, the owner separately authorized
  publishing the updated source and reviewed Windows preview to
  `AgentMindCloud/ProdOS`. It is now public under
  [preview-0.2.0](https://github.com/AgentMindCloud/ProdOS/releases/tag/preview-0.2.0);
  see [GitHub publication evidence](GITHUB_RELEASE.md).

## Authorized local preparation

- Static website source: `website/`.
- Build tool: `scripts/build_website.py`.
- Output: `.work/website-dist/`.
- Reviewed app: `release-artifacts/ProducerOS-0.2.0-Windows.zip`.
- Deployment archive: `release-artifacts/prodos-site-20260909.zip`.
- Independent website/download checks: `tests/website/`.

The app package's existing SHA-256 and ZIP structure were checked before
including it. It is still a portable Windows preview. The desktop backend,
user data, settings and music folders have not been altered for the website.

## Verification and publication status

- Site build completed: 17 allowlisted files; deploy ZIP 30,880,168 bytes.
  SHA-256: `d7cb464902f8db3d671529efe8b2de6a2e8d49e39668903eb58f1d7e8c2bd584`.
- Website suite: **10 passed**, including isolated project edits, literal HTML
  input, reset/reload behavior, no persistence/external requests, original
  audio playback/seeking/reset, responsive controls at 360/390/768/1440 px,
  full browser ZIP download/hash, no-JS FAQ/download guidance and share fallback.
- Real in-app Chromium visual review of desktop hero/demo and 390 px homepage
  completed. A decorative ellipse overflow was fixed; independent Chromium
  measurements found no overflow at 14 widths from 320 to 1440 px. Physical
  phones and browsers other than Chromium were not tested.
- Ruff formatting/lint and JavaScript syntax checks passed for the new code.
- Independent review checked archive allowlist/integrity, local links/anchors,
  source/build equality, synthetic screenshot and valid 17.14-second PCM demo.
  Its full HTTP app download matched the reviewed Windows SHA-256. No material
  website privacy or distribution defect remained in that bounded review.
- Local preview: `http://127.0.0.1:8427/`, using `scripts/preview_website.py`.
  A plain Python HTTP server could not support browser audio seeking correctly;
  the preview/test server now serves byte ranges like a static production host.

The owner explicitly approved publishing this reviewed site and Windows preview
to prodos.tech using the existing Business hosting account. Do not request that
publication approval again.

## Published and checked

The site is now live at **https://prodos.tech/**. Earlier File Manager 403 errors
were resolved after the owner opened a working session. Their precise cause
was not established; no permissions, passwords, DNS or security settings were
changed to work around them. Keep session/auth URLs out of documentation.

The approved archive was successfully uploaded. The owner extracted it into an
extra `public_html/public_html` folder. The nine approved top-level entries
(including the hidden `.htaccess`, assets and downloads) were moved up to the
real `public_html`. The parent folder was checked before that move; no existing
site file was overwritten. Hostinger's `default.php` remains, as do the deploy
archive and the now-empty extraction folder.

Fresh checks against the public site on 2026-09-09:

- HTTPS rendered the actual ProducerOS headline, styling, artwork and demo.
  No certificate warning was bypassed.
- The public Download ProducerOS button downloaded **28,216,733 bytes** to
  `Downloads/ProducerOS-0.2.0-Windows (1).zip` at approximately 23:31 local time.
  Its SHA-256 is
  `1e72d6a8f23ff4949d92c8b9be7b3c3e4e80a42c32cd84ed99ce5146af21bb55`,
  exactly matching the reviewed package. ZIP CRC integrity and the expected
  `ProducerOS/ProducerOS.exe` entry were checked locally on this downloaded copy.
- Live project selection, title editing, stage changes, checklist and reset
  worked. The native player played and sought to 0:08 of the 17-second demo.
- FAQ expansion worked. The live browser error/warning log was empty during
  these checks. The public homepage was visually checked at 390 px width;
  the temporary viewport override was then reset.

The direct HTTP test client still receives Hostinger's browser-check challenge
(403). Therefore actual origin/CDN security and cache headers were not verified
from that client; do not present its challenge headers as the site's headers.
The intended `.htaccess` was deployed and local tests enforce its intended CSP.
No independent crawler, social-link-preview or physical-phone test is claimed.
No app backend, music, account data or source repository was deployed.

Keep Hostinger's `default.php` in place. The new site's `DirectoryIndex`
selects `index.html` without deleting the placeholder. Future rollback can
use the previous recorded archive and hashes; do not reset DNS or delete
existing files as a shortcut.
