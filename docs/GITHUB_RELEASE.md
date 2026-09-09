# GitHub publication evidence

## Update: 0.2.1 file safety preview, 2026-09-10

[preview-0.2.1](https://github.com/AgentMindCloud/ProdOS/releases/tag/preview-0.2.1)
is published at `37e5eb4c0de7ffd3d2cf1b112d246ce74c7eae28`. The app ZIP,
checksum and portable guide are the only attached assets. GitHub's generated
source ZIP/tar archives are separate. The complete public app download matched
SHA-256 `b2a4eba0421139bd6c4c70b9a8ace2494e4f7e80e89bcda43a28cca8cb224863`
(28,211,113 bytes) and passed ZIP integrity. Older release notes direct users
to 0.2.1 for the safety changes; old binaries do not update automatically.

The two website deployment ZIP/checksum assets were removed from 0.2.0. The new
bundle was deployed separately to Hostinger after correcting nested extraction.
The public website now displays 0.2.1; its complete Windows download matches the
same reviewed hash. No website ZIP is attached to the new GitHub release. See
[current verification and limits](review-2026-09-10/REVIEW.md) and `HANDOFF.md`.

## Original publication: 0.2.0

Published with the owner's explicit authorization on 2026-09-09 at
16:55:23 UTC. This publishes the existing reviewed app and companion site;
it does not add a network dependency to the desktop app.

- Public repository: https://github.com/AgentMindCloud/ProdOS
- Website: https://prodos.tech/
- Preview release: https://github.com/AgentMindCloud/ProdOS/releases/tag/preview-0.2.0
- Release source commit: `5333005eefa42a10a10ac7e107f20edc8fdaf122`.
- The release is published, explicitly marked as a prerelease, and does not
  replace the older stable 0.1.0 release. The tag resolves to the source commit
  above. Subsequent documentation-only commits do not move that tag.

## Files actually published

| Asset | Bytes | SHA-256 |
|---|---:|---|
| ProducerOS-0.2.0-Windows.zip | 28,216,733 | `1e72d6a8f23ff4949d92c8b9be7b3c3e4e80a42c32cd84ed99ce5146af21bb55` |
| prodos-site-20260909.zip | 30,880,168 | `d7cb464902f8db3d671529efe8b2de6a2e8d49e39668903eb58f1d7e8c2bd584` |

Both SHA-256 sidecars and `WINDOWS_PORTABLE.txt` were attached at publication.
GitHub's reported upload digests matched all five local files. An unauthenticated
request to the public Windows download returned HTTP 200 and streamed all
28,216,733 bytes; the computed hash matched the reviewed package above.

The source update preserves the repository's original Git history and MIT
license. The older tracked installer is unchanged. Runtime databases, review
accounts, configuration, session keys, logs, local scratch data and real music
were excluded. Independent bounded source review found no remaining publication
blocker. The unchanged reviewed Windows bundle retains nonsecret build paths
inside cached migration bytecode; it was not rebuilt just to alter metadata.

## Download-list cleanup on 2026-09-10

After the owner raised concern about the deployment downloads, the two
`prodos-site-20260909.zip` / `.zip.sha256` assets were removed from the GitHub
release and the release notes were corrected. The release now has only the
Windows ZIP, its checksum and `WINDOWS_PORTABLE.txt`, in addition to GitHub's
automatic source archives. The Windows ZIP digest is unchanged. The local
website deployment backup and live Hostinger site were not changed.

The inspected deployment bundle contained 17 allowlisted public website/demo
files, including the same Windows package. Its hash matched the published asset;
ZIP integrity passed and no runtime database, configuration or secret-key filename
was present in the nested Windows archive. The deployment ZIP was unnecessary for
app users, rather than evidence of a credential or private-music exposure. Website
source remains public in the repository.

## Verification from the publication checkout

- Unit/integration/security: **161 passed, 3 skipped**. The skips are documented
  Windows filesystem/symlink limitations; one test-client deprecation warning remains.
- Application browser checks: **6 passed**.
- Website checks: **10 passed**, after rebuilding from the publication checkout
  and supplying the exact reviewed Windows ZIP as documented in `website/README.md`.
- Ruff lint and formatting passed; mypy reported no issues in 89 source files.
- Staged diff passed whitespace checks; only intended source, public artwork,
  synthetic screenshots, tests and documentation were included.
- GitHub Security workflow passed for the release commit:
  https://github.com/AgentMindCloud/ProdOS/actions/runs/34379663206
- GitHub Windows Build passed, including a separate CI installer build, silent
  installation/shortcut/launch checks and uninstall smoke test:
  https://github.com/AgentMindCloud/ProdOS/actions/runs/34379663244
  That CI artifact does not replace the reviewed portable preview attached here.
- GitHub's Ubuntu and Windows CI jobs both passed, confirmed on 2026-09-10:
  https://github.com/AgentMindCloud/ProdOS/actions/runs/34379663303

Run app and website browser suites as separate pytest commands, as documented.
Running both together leaves the app's session-scoped Playwright runtime alive
when the website starts another runtime, producing a fixture setup conflict.
This is a test-harness limitation; separate runs passed. No new clean-machine,
physical-phone, large-library, signed-installer or upgrade certification is claimed.

The reviewed source has already been published and the existing Hostinger site
was not altered during GitHub publication. No further permission is needed for
this completed, explicitly authorized publication.
