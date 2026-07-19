# Installing ProducerOS on Windows

Two ways to get ProducerOS running: download a built release, or build it
yourself from source. Either way, no separate Python install is required
to *run* it -- only to *build* it.

## Option A: Download a release (recommended)

1. Go to the repository's [Releases](../../releases) page and download
   the newest `ProducerOS-vX.Y.Z-windows.zip`.
2. Verify the checksum: right-click the downloaded zip, or run
   ```powershell
   Get-FileHash .\ProducerOS-vX.Y.Z-windows.zip -Algorithm SHA256
   ```
   and compare the output against the accompanying `.sha256` file from
   the same release.
3. Extract the zip somewhere you have write access (e.g.
   `C:\Users\<you>\ProducerOS\`). Keep `ProducerOS.exe` and the
   `_internal\` folder next to each other -- the `.exe` alone will not
   run without it (see
   [ADR 0005](adr/0005-pyinstaller-onedir-frozen-path-resolution.md)).
4. Double-click `ProducerOS.exe`. A console window opens showing startup
   logs, database migrations run automatically on first launch, and your
   default browser opens to the dashboard at `http://127.0.0.1:8420/`.
5. First run takes you to `/setup` to create your one admin account.

Your data (database, logs, backups, generated secret key) lives at
`%LOCALAPPDATA%\ProducerOS\` -- never inside the install folder, so it
survives reinstalling or moving the app folder.

## Option B: Build from source

Requires [Python 3.12](https://python.org) on PATH and
[git](https://git-scm.com/).

```powershell
git clone https://github.com/AgentMindCloud/ProdOS.git
cd ProdOS
.\scripts\setup_windows.ps1      # creates .venv, installs ProducerOS + dev deps
.\scripts\run_tests.ps1          # optional: confirm everything passes on your machine
.\scripts\build_windows.ps1      # produces dist\ProducerOS\ProducerOS.exe
.\scripts\run_desktop.ps1        # run it (uses the built exe if present, else runs from source)
```

See `packaging/README.md` for what the build actually bundles and what
has/hasn't been verified on real Windows.

## Running modes

- **Desktop mode** (default): binds to `127.0.0.1` only, nothing else on
  your network can reach it. `.\scripts\run_desktop.ps1` or
  `ProducerOS.exe run --mode desktop`.
- **LAN mode**: binds to your machine's private network address so a
  paired Android phone can connect. `.\scripts\run_lan.ps1` or
  `ProducerOS.exe run --mode lan`. See `docs/ANDROID_PWA.md`. Never
  forward this port through your router.

## Uninstalling

Delete the folder you extracted (or `dist\ProducerOS\` if built from
source), then delete `%LOCALAPPDATA%\ProducerOS\` if you also want to
remove your data -- back it up first (`docs/BACKUP_RESTORE.md`) if there's
any chance you'll want it again.

## Troubleshooting

See `docs/TROUBLESHOOTING.md`. The short version: a startup failure shows
a Windows message box with the error, and a full log is always at
`%LOCALAPPDATA%\ProducerOS\logs\produceros.log`.
