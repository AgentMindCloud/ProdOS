# Building ProducerOS

How to go from this source tree to the `ProducerOS-Setup-X.Y.Z.exe` that a
non-technical user double-clicks.

There are two ways to get one, and **you almost never need the second**:

| | Where it runs | When to use it |
|---|---|---|
| [CI build](#1-let-github-build-it-recommended) | GitHub's Windows runners | Every real release. No tools to install. |
| [Local build](#2-building-it-yourself-on-windows) | Your own Windows PC | Debugging packaging itself. |

You cannot build a Windows installer on Linux or macOS. PyInstaller freezes
for the machine it runs on, so a Windows `.exe` needs Windows.

---

## 1. Let GitHub build it (recommended)

`.github/workflows/release.yml` runs the whole pipeline: full validation,
PyInstaller bundle, Inno Setup installer, checksums, SBOM, and the GitHub
release itself. Two ways to start it — they produce identical results.

**Push a tag:**

```bash
git checkout main
git pull
git tag v0.1.1
git push origin v0.1.1
```

**Or start it from the browser** (useful when you can't push tags):
Actions tab → **Release** → *Run workflow* → enter `v0.1.1` → Run.
The workflow creates the tag itself if it doesn't exist.

Either way, ~10–15 minutes later
<https://github.com/AgentMindCloud/ProdOS/releases> has:

```
ProducerOS-Setup-0.1.1.exe                  <- the installer
ProducerOS-Setup-0.1.1.exe.sha256
ProducerOS-0.1.1-windows-portable.zip       <- no-installer alternative
ProducerOS-0.1.1-windows-portable.zip.sha256
sbom.json                                   <- CycloneDX dependency list
```

### Before you tag

- Bump `version` in `pyproject.toml` to match the tag (without the `v`).
  The workflow passes the tag's version to the build, so a mismatch means
  the installer's version and the source's version disagree.
- Update `CHANGELOG.md`.
- Make sure `main` is green in the Actions tab.

### What gates a release

The `validate` job runs lint (ruff format + check), types (mypy), the
unit/integration/security suites, an Alembic migration check on a fresh
database, and a demo-data load/clean round trip. `build-windows` then
proves the installer actually compiles.

The Playwright e2e suite is deliberately **not** a release gate
(`run_e2e: false`) because its fixtures leak state between tests on ubuntu
runners. It still runs on every push and PR. See `HANDOFF.md` for the
diagnosis to finish, and remove that flag once it's fixed.

---

## 2. Building it yourself on Windows

### Prerequisites

1. **Python 3.11+** from <https://python.org> — tick "Add Python to PATH".
2. **Inno Setup 6** from <https://jrsoftware.org/isdl.php> — the default
   install location is fine; the build script finds `ISCC.exe` on PATH or
   under `Program Files`.

### One-time setup

```powershell
git clone https://github.com/AgentMindCloud/ProdOS.git
cd ProdOS
.\scripts\setup_windows.ps1
```

That creates `.venv` and installs ProducerOS in editable mode with dev
extras. If PowerShell refuses to run the scripts, allow local ones for
this session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Build the installer

```powershell
.\scripts\build_installer.ps1
```

Version comes from `pyproject.toml`; override it with
`-Version "0.1.1"`. Output:

```
installer-output\ProducerOS-Setup-<version>.exe
```

That single file is the whole deliverable.

### Build only the frozen app (no Inno Setup needed)

```powershell
.\scripts\build_windows.ps1
```

Output:

```
dist\ProducerOS\
  ProducerOS.exe
  _internal\        <- Python runtime, deps, templates, static, migrations
```

Distribute the **whole `dist\ProducerOS\` folder**, never `ProducerOS.exe`
on its own — it cannot run without `_internal\`.

### Check it before shipping

```powershell
.\scripts\run_tests.ps1                  # full suite
.\dist\ProducerOS\ProducerOS.exe run     # should open a browser at 127.0.0.1:8420
```

Then install the built `.exe` on a machine that has never had ProducerOS,
confirm the desktop icon appears and launches the app, and confirm that
re-running the installer over an existing install upgrades it without
touching `%LOCALAPPDATA%\ProducerOS\`.

---

## 3. Refreshing the committed installer

This repo commits the current installer to `installer/` so that "Code →
Download ZIP" contains something runnable (see
[`../installer/README.md`](../installer/README.md)). That file does **not**
update itself — after each release:

1. Download the new `ProducerOS-Setup-X.Y.Z.exe` **and** its `.sha256`
   from the Releases page. Use the CI-built artifact, not a local build,
   so the committed binary matches a reproducible, published one.
2. Verify it: the hash you compute must equal the published one.
   ```powershell
   Get-FileHash installer\ProducerOS-Setup-X.Y.Z.exe -Algorithm SHA256
   ```
3. Delete the previous `.exe` and `.sha256` from `installer/` — keep only
   the newest pair, so git history grows by one binary per release rather
   than accumulating them side by side.
4. Update the version numbers named in `START-HERE.txt` and
   `installer/README.md`.
5. Commit: `git add -A installer START-HERE.txt && git commit`.

`.gitignore` ignores stray `ProducerOS-*.exe` everywhere except this
folder, so a local build sitting in `installer-output\` can never be
committed by accident.

---

## 4. How the packaging works

Design detail lives next to the code:

- [`../packaging/README.md`](../packaging/README.md) — what's bundled, why
  the build is windowed, what was and wasn't verified.
- [ADR 0005](adr/0005-pyinstaller-onedir-frozen-path-resolution.md) — why
  frozen paths resolve through `sys._MEIPASS`.
- [ADR 0006](adr/0006-inno-setup-installer.md) — why Inno Setup, per-user
  install, and a fixed `AppId`.

Two things that bite people modifying the build:

- **`console=False`.** Windows gives a windowed process
  `sys.stdout`/`sys.stderr` of `None`; `launcher.py` redirects both before
  anything prints. Logs still go to
  `%LOCALAPPDATA%\ProducerOS\logs\produceros.log`.
- **The `AppId` GUID in `packaging/inno/producer-os.iss` must never
  change.** It's what makes a new installer upgrade the existing install
  instead of appearing as a second, separate program.

## 5. Signing

The installer is unsigned, so Windows SmartScreen shows "Windows protected
your PC" on first run ("More info" → "Run anyway"). Signing needs a paid
code-signing certificate; see `ROADMAP.md`.
