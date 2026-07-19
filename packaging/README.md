# Packaging ProducerOS for Windows

ProducerOS ships as a standalone, PyInstaller-built Windows executable so a
producer can run it with no separately-installed Python and no internet
access after the download. This directory holds the PyInstaller build
config; the PowerShell scripts that call it live in `../scripts/`.

## Layout

- `pyinstaller/produceros.spec` -- the PyInstaller build spec. Bundles:
  - `src/produceros/web/templates/` and `src/produceros/web/static/`
    (Jinja templates, CSS/JS/icons/PWA manifest)
  - `migrations/` and `alembic.ini` (so the frozen build can migrate its
    own database via `produceros.cli.cmd_db_upgrade`, which uses
    Alembic's Python API rather than the `alembic` CLI)
  - hidden imports for uvicorn's protocol/loop auto-selection, Alembic,
    and `mcp.server.fastmcp` (lazily imported only when MCP is enabled,
    so PyInstaller's static analysis needs the hint)
- `pyinstaller/launcher.py` -- the actual entry point PyInstaller freezes.
  Forwards real `argv` (e.g. `--mode lan`, `--port`) into
  `produceros.cli.main`, defaulting to `["run"]` only when the exe was
  double-clicked with no arguments. Wraps startup in a broad
  `try/except` so a failure shows a Windows message box instead of the
  process silently vanishing.

## Building

From a Windows machine with the dev environment set up
(`scripts\setup_windows.ps1`):

```powershell
.\scripts\build_windows.ps1
```

This runs `pyinstaller packaging\pyinstaller\produceros.spec --noconfirm`
and produces a **onedir** build at `dist\ProducerOS\`:

```
dist\ProducerOS\
  ProducerOS.exe          <- what the user runs / what run_desktop.ps1 calls
  _internal\               <- bundled Python runtime, deps, templates, static, migrations, alembic.ini
```

PyInstaller 6's onedir layout puts every bundled data file (`datas` in the
spec) under `_internal\`, not next to the exe -- `produceros.cli._alembic_config()`
resolves this at runtime via `sys._MEIPASS` rather than assuming a flat
layout, since that assumption previously broke migrations in a frozen
build (caught by an actual smoke-test run of the built exe, not just a
successful `pyinstaller` build).

To distribute the app, zip the whole `dist\ProducerOS\` folder -- the
`.exe` alone will not run without `_internal\`.

## What was actually verified, and what wasn't

This spec and launcher were built and smoke-tested from this repo's Linux
container, which can run PyInstaller and produce a **Linux** ELF binary
using the same spec file (PyInstaller ignores the target OS and just
freezes for the host platform it runs on). That Linux build was smoke
tested for real:

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

**Not verified**: an actual Windows `.exe` has not been built or run on
real Windows from this session -- there is no Windows machine available
here. The spec is expected to produce a working `.exe` on
`windows-latest` (see `.github/workflows/windows-build.yml`, which builds
and smoke-tests on a real Windows GitHub Actions runner), but that
workflow has not yet been triggered/observed passing. Treat the Windows
`.exe` as build-config-verified-by-analogous-Linux-build, not
Windows-verified, until a `windows-build.yml` run (or a manual build on
real Windows) confirms it.

## Windowed vs. console build

The spec currently builds with `console=True`, so a console window stays
open showing startup/log output -- useful for a producer to see errors
immediately, and it means `launcher.py`'s message-box fallback is a
backstop rather than the primary error channel. If a windowed
(no-console) build is wanted later, flip `console=False` in
`produceros.spec`; the message-box error path in `launcher.py` already
handles that case (it's currently redundant belt-and-suspenders with the
console output).
