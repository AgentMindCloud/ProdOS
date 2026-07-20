# Admin Guide

Operational tasks for running ProducerOS day to day: configuration,
backups, LAN devices, scanner roots, and the demo dataset. For the
feature walkthrough see `docs/USER_GUIDE.md`.

## Configuration

ProducerOS runs with zero required configuration. Every setting has a
safe local default (`config.py`). To override one, either set an
environment variable prefixed `PRODUCEROS_` (e.g. `PRODUCEROS_PORT=9000`)
or edit `config.toml` in the data directory (copy `config.example.toml`
from the repo as a starting point) -- environment variables take
precedence over the file.

Notable settings:

| Setting | Default | Purpose |
|---|---|---|
| `bind_mode` | `desktop` | `desktop` (127.0.0.1 only) or `lan` |
| `port` | `8420` | Web app port |
| `open_browser` | `true` | Auto-open a browser tab on `run` |
| `pairing_code_ttl_minutes` | `10` | LAN pairing-code lifetime |
| `pairing_rate_limit_per_minute` | `5` | LAN pairing-attempt throttle |
| `db_wal_mode` | `true` | SQLite WAL mode |
| `log_level` | `INFO` | Logging verbosity |
| `mcp_enabled` | `false` | Local MCP server (see `docs/MCP.md`) |

## Data directory

Everything ProducerOS writes lives under one directory, never inside the
install/app folder:

- Windows: `%LOCALAPPDATA%\ProducerOS\`
- Contents: `produceros.db` (the database), `secret.key` (session-signing
  key, generated once), `logs\produceros.log` (rotating, secrets
  redacted), `backups\`, `audio_cache\`, `config.toml` (if you created
  one).

Back this whole directory up externally from time to time in addition to
using the in-app backup feature -- it's the entire state of the
application.

## Backups

See `docs/BACKUP_RESTORE.md` for the full walkthrough. Short version:
`ProducerOS.exe backup-create` (or the Backup page, or
`.\scripts\backup.ps1`) any time; consider scheduling it (e.g. Windows
Task Scheduler running `scripts\backup.ps1` daily).

## Scanner roots

Settings/Scanner page: add the folders ProducerOS should watch (e.g.
`D:\Music\Projects`, `D:\Music\Exports`). Only files under an allowed
root, with an allowed extension, and under the configured size limit are
ever considered. The scanner is read-only regardless of what roots are
configured -- see `docs/SECURITY_MODEL.md`.

## LAN devices

Settings -> LAN mode & devices: generate pairing codes for new phones,
revoke access for any device at any time. See `docs/ANDROID_PWA.md` for
the pairing walkthrough from the phone side.

## Demo data

`ProducerOS.exe demo-load` populates a realistic sample catalog (see
`docs/USER_GUIDE.md`); `demo-clean` removes exactly those rows via a
precise creation-time manifest, leaving any real data you've entered
untouched. Useful for a fresh evaluation, a screenshot pass, or
onboarding someone new to the app before they add real projects.

## Audit trail

Every state-changing action (login, project edits, rights changes, file
operations, backups, device pairing/revocation, and more) is recorded as
an `AuditEvent` (`services/audit.py`) -- there's no dedicated audit-log
page yet, but the data is there for future tooling or direct database
inspection if you need to answer "who/what changed this and when."

## Logs

`%LOCALAPPDATA%\ProducerOS\logs\produceros.log`, JSON-formatted, rotating
(5MB x 5 backups), with secrets automatically redacted before they're
ever written (`docs/SECURITY_MODEL.md`). Safe to attach to a bug report
as-is.

## Upgrading

If ProducerOS was installed with the installer (`ProducerOS-Setup-X.Y.Z.exe`,
the recommended path -- see `docs/INSTALL_WINDOWS.md`): back up first
(`docs/BACKUP_RESTORE.md`), then download and run the new version's
installer the same way you ran the first one. It upgrades in place --
same shortcuts, same install location, same data -- with no uninstall
step needed. Migrations run automatically on the next launch.

If running the portable zip build instead: back up first, then replace
the old `dist\ProducerOS\` folder with the new one (your data directory
is untouched either way since it lives outside the app folder). Launch
it; migrations run automatically.

## Uninstalling

Installer-based install: Windows Settings -> **Apps** -> **ProducerOS**
-> **Uninstall**. This only removes the installed application; your data
at `%LOCALAPPDATA%\ProducerOS\` is left alone automatically (the
uninstaller shows a message confirming this). Delete that folder yourself
if you also want to remove your data (back it up first if there's any
chance you'll want it again).

Portable zip install: delete the app folder, and
`%LOCALAPPDATA%\ProducerOS\` if you also want to remove your data.
