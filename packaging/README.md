# Packaging ProducerOS for Windows

ProducerOS ships as a proper Windows installer -- a producer downloads one
`.exe`, double-clicks it, and gets a Start Menu entry and a desktop icon
with no separately-installed Python, no admin rights, and no internet
access needed after the download. This directory holds both build stages;
the PowerShell scripts that call them live in `../scripts/`. See
`../docs/INSTALL_WINDOWS.md` for the end-user instructions and
[ADR 0006](../docs/adr/0006-inno-setup-installer.md) for why it's built
this way.

## Layout

- `pyinstaller/produceros.spec` -- the PyInstaller build spec, producing a
  **onedir** bundle (`ProducerOS.exe` + `_internal\`). Bundles:
  - `src/produceros/web/templates/` and `src/produceros/web/static/`
    (Jinja templates, CSS/JS/icons/PWA manifest)
  - `migrations/` and `alembic.ini` (so the frozen build can migrate its
    own database via `produceros.cli.cmd_db_upgrade`, which uses
    Alembic's Python API rather than the `alembic` CLI)
  - hidden imports for uvicorn's protocol/loop auto-selection, Alembic,
    and `mcp.server.fastmcp` (lazily imported only when MCP is enabled,
    so PyInstaller's static analysis needs the hint)
  - Built **windowed** (`console=False`): double-clicking the desktop icon
    should feel like launching a normal app, not a terminal program. Every
    log line that would have gone to a console still reaches
    `%LOCALAPPDATA%\ProducerOS\logs\produceros.log`.
  - Embeds `app-icon.ico` (see below) so the exe, taskbar, and shortcuts
    all show the real ProducerOS mark.
- `pyinstaller/launcher.py` -- the actual entry point PyInstaller freezes.
  Forwards real `argv` (e.g. `--mode lan`, `--port`) into
  `produceros.cli.main`, defaulting to `["run"]` only when the exe was
  double-clicked with no arguments. Wraps startup in a broad
  `try/except` so a failure shows a Windows message box instead of the
  process silently vanishing. Also fixes a real windowed-build gotcha:
  Windows hands a windowed process `sys.stdout`/`sys.stderr` of `None`
  (no console to write to), which would otherwise crash on the first
  `print()` or log line -- `_fix_windowed_stdio()` redirects both to a
  null sink before anything else runs.
- `pyinstaller/app-icon.ico` -- generated (not hand-drawn) by
  `scripts/generate_icons.py`, the same script that produces the PWA web
  icons. A modern `.ico` can embed PNG-compressed frames directly, so the
  existing dependency-free PNG encoder packs straight into a valid
  multi-resolution icon (16/32/48/256px) with no image library. Re-run
  `python scripts/generate_icons.py` any time the icon design changes;
  the output is committed like the other icon assets.
- `inno/producer-os.iss` -- the [Inno Setup](https://jrsoftware.org/isinfo.php)
  installer script. Per-user install (no admin rights, no UAC prompt),
  Start Menu entry, optional desktop icon (checked by default), proper
  "Apps & features" uninstaller, and upgrade-in-place across versions via
  a fixed `AppId`.

## Building

From a Windows machine with the dev environment set up
(`scripts\setup_windows.ps1`) and [Inno Setup](https://jrsoftware.org/isdl.php)
installed (`windows-latest` GitHub Actions runners already have it):

```powershell
.\scripts\build_installer.ps1
```

This builds the PyInstaller bundle, then compiles the installer, producing
`installer-output\ProducerOS-Setup-<version>.exe` -- the single file
described in `docs/INSTALL_WINDOWS.md`. Pass `-Version "1.2.3"` to set the
embedded version explicitly (CI does this from the git tag); otherwise it
reads `version` from `pyproject.toml`.

To build just the raw PyInstaller bundle (no Inno Setup needed, useful
during development, or as a no-installer "portable" alternative):

```powershell
.\scripts\build_windows.ps1
```

produces:

```
dist\ProducerOS\
  ProducerOS.exe          <- what run_desktop.ps1 calls, and what the installer bundles
  _internal\               <- bundled Python runtime, deps, templates, static, migrations, alembic.ini
```

PyInstaller 6's onedir layout puts every bundled data file (`datas` in the
spec) under `_internal\`, not next to the exe -- `produceros.cli._alembic_config()`
resolves this at runtime via `sys._MEIPASS` rather than assuming a flat
layout, since that assumption previously broke migrations in a frozen
build (see [ADR 0005](../docs/adr/0005-pyinstaller-onedir-frozen-path-resolution.md)).
The installer's `[InstallDelete]` step wipes and replaces this whole
folder on every install/upgrade, so a portable zip distribution needs the
same rule: distribute the whole `dist\ProducerOS\` folder, never the
`.exe` alone.

## What was actually verified, and what wasn't

This spec and launcher were built and smoke-tested from this repo's Linux
container, which can run PyInstaller and produce a **Linux** ELF binary
using the same spec file (PyInstaller ignores the target OS and just
freezes for the host platform it runs on; the Windows-only `icon=` and
`console=False` settings are silently no-ops there). That Linux build was
smoke tested for real:

- `pyinstaller packaging/pyinstaller/produceros.spec` completes without
  missing-module errors.
- The frozen binary runs `produceros run --no-browser --port <N>`,
  applies Alembic migrations, starts the web server, and serves a real
  `200` response on `/setup`.
- `db-upgrade`, `db-current`, `demo-load`, `demo-clean`, `backup-create`,
  `restore-dry-run`, and `restore` all run correctly through the frozen
  binary.
- Argument forwarding through `launcher.py` was verified by confirming
  `--port` actually changes the bound port in the frozen build (an
  earlier version of the launcher hardcoded `["run"]` and silently
  ignored every flag -- caught by this same smoke test).
- The generated `app-icon.ico` was verified structurally (valid ICO
  container, 4 correctly-offset frames, each a valid PNG with the right
  magic bytes) and visually (the 256px frame renders as the intended
  mark), since there's no Windows Explorer here to eyeball a shortcut
  icon in.

**Not verified in this environment** (no Windows machine, no Inno Setup
available here): that the `.iss` script actually compiles, that the
compiled installer actually runs a silent install, creates real Start
Menu/desktop shortcuts, and that uninstalling actually leaves
`%LOCALAPPDATA%\ProducerOS\` alone. `.github/workflows/windows-build.yml`
checks exactly these things on a real `windows-latest` runner, but that
workflow has not yet been triggered/observed passing from this session.
Treat the installer as syntax-reviewed and Linux-smoke-tested-by-analogy,
not Windows-verified, until that CI run is observed passing --
[ADR 0006](../docs/adr/0006-inno-setup-installer.md) has the same caveat
in more detail.

## Signing

The installer is currently unsigned, so Windows SmartScreen shows a
"Windows protected your PC" warning on first run (documented in
`docs/INSTALL_WINDOWS.md` -- "More info -> Run anyway"). Code-signing
requires a paid certificate and isn't set up; see `ROADMAP.md`.
