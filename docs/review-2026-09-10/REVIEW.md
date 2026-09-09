# ProdOS 0.2.1 file safety review

The owner's rule is implemented: approved moves/renames remain possible;
deleting and overwriting user files are unavailable. Scanning and playback
remain read-only. See [the policy](../FILE_SAFETY.md) for behavior and limits.

## Changes

- Reject DELETE and REPLACE, including old approved operations. Copy creates a
  new file exclusively; native rename refuses occupied destinations and never
  falls back to copying then deleting across filesystems.
- Delivery preflights the entire manifest, requires a new absolute output
  folder, validates asset ownership and rejects traversal, path collisions,
  Windows aliases and linked destinations. Partial exports are retained.
- Demo generation uses unique folders and exclusive writes. Cleanup removes
  demo database records only, preserving disk files and unrelated records.
- App storage rejects linked files/directories. Snapshot and restore staging
  use exclusive unique filenames. External backup checks use immutable SQLite
  reads and reject pending WAL data, preventing sidecar creation/overwrites.
- Package migration assets exclude cached developer bytecode. Website and
  download guides describe this version without changing the approved design.

Own database/settings/log writes and a confirmed restore of the app's own
metadata database are necessary and remain supported. No external service,
background updater, local website bridge or new file-management UI was added.

## Evidence observed on Windows, 2026-09-10

| Check | Result |
| --- | --- |
| Unit, integration and security suites | 222 passed, 8 platform/permission skips |
| App Chromium flows | 6 passed |
| Website Chromium flows, responsive demo, audio, complete download hash | 10 passed |
| Ruff lint / format | Passed, 140 files formatted |
| mypy | Passed, 90 source files |
| Fresh PyInstaller executable | Build passed |
| Packaged CLI migrations + demo load/cleanup | Passed; all 7 test file hashes preserved |
| Packaged setup/login, 21 routes, project creation, backup validation, redirect guard, quit | Passed in isolated app storage |
| ZIP integrity and runtime/private filename exclusions | Passed; 301 entries |
| Independent file-collision / rename / SQLite sidecar checks | Passed after reproducing and fixing the SQLite defect |

The independent review demonstrated that SQLite `mode=ro` alone could modify
a neighboring `-shm` file. The final immutable-backup checks preserved valid
and invalid backup candidates and all their sibling files byte for byte.
All test inputs were synthetic, in isolated temporary directories.

## Reviewed download

`ProducerOS-0.2.1-Windows.zip`: **28,211,113 bytes**.

SHA-256: `b2a4eba0421139bd6c4c70b9a8ace2494e4f7e80e89bcda43a28cca8cb224863`.

The website deployment ZIP contains 17 allowlisted public files and stays local;
it is not a GitHub release asset. Source and hosting publication status is in
`HANDOFF.md`; an old binary does not change when new source is published.

## Limits

An ordinary desktop process is not an OS sandbox. These controls do not prove
immunity to compromised software, hostile simultaneous filesystem changes or
every future defect. Linux native rename behavior requires its CI run; no
macOS/Linux package, clean recipient PC, interactive upgrade/uninstall, physical
mobile or large-library performance result is claimed here. The Windows binary
is an unsigned portable preview; the legacy installer remains unchanged.
