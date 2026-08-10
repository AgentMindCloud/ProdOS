# installer/

This folder holds the **ready-to-run Windows installer** for the current
release, committed into the repository on purpose.

```
ProducerOS-Setup-0.1.0.exe          <- double-click this on Windows
ProducerOS-Setup-0.1.0.exe.sha256   <- checksum, to prove it wasn't corrupted
```

## Why it's committed (most projects don't do this)

So that **"Code -> Download ZIP" produces something usable by someone who
doesn't code**. Normally the built `.exe` lives only on the
[Releases page](https://github.com/AgentMindCloud/ProdOS/releases) and a
repo ZIP contains source code and nothing runnable. Here, the ZIP contains
`START-HERE.txt` at the top level and this installer — which is the whole
handoff, in one file you can send over WhatsApp or Drive.

The trade-off, so it's on the record: the `.exe` is ~23 MB, and git keeps
every committed version forever. Ten releases means roughly a quarter of a
gigabyte in history that every clone pays for. That's a deliberate,
acceptable price for this project — it's a two-person tool, not a
widely-cloned library. To keep the growth as slow as possible, **replace**
this file when releasing rather than adding a second one: only the newest
installer should ever be present here.

## Where this exact file came from

It is not built by hand. It is the artifact from
[release v0.1.0](https://github.com/AgentMindCloud/ProdOS/releases/tag/v0.1.0),
built by `.github/workflows/release.yml` on a real `windows-latest` runner
from this repository's source, then downloaded and committed unchanged.
The SHA-256 above matches the checksum published alongside that release,
so you can confirm the committed file is byte-for-byte the CI-built one:

```powershell
# Windows PowerShell, from the repo root
Get-FileHash installer\ProducerOS-Setup-0.1.0.exe -Algorithm SHA256
```

```bash
# macOS / Linux
sha256sum -c installer/ProducerOS-Setup-0.1.0.exe.sha256
```

## Updating this file for a new release

See [`docs/BUILDING.md`](../docs/BUILDING.md) — section "Refreshing the
committed installer". Short version: cut the release tag, let CI build it,
download the `.exe` and its `.sha256` from the Releases page, delete the
old pair here, commit the new pair, and update the version numbers named
in `START-HERE.txt`.

## Installing it

End users: [`../START-HERE.txt`](../START-HERE.txt).
More detail: [`../docs/INSTALL_WINDOWS.md`](../docs/INSTALL_WINDOWS.md).
