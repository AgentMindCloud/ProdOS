# Troubleshooting

## The .exe does nothing when double-clicked / closes immediately

Look for a Windows message-box error (a broad `try/except` around startup
shows one instead of the process silently vanishing --
`packaging/pyinstaller/launcher.py`). Also check
`%LOCALAPPDATA%\ProducerOS\logs\produceros.log` -- it's written before
the web server starts, so it captures migration failures too.

If you copied only `ProducerOS.exe` without its `_internal\` folder, it
won't run -- see [ADR 0005](adr/0005-pyinstaller-onedir-frozen-path-resolution.md).
Keep the whole `dist\ProducerOS\` (or extracted release zip) folder
together.

## "Path doesn't exist" / Alembic errors on first launch

This was a real bug in early builds (bundled `migrations/`/`alembic.ini`
weren't found in a frozen build's actual layout) -- fixed and covered by
a smoke test in `windows-build.yml`. If you see this on a build newer
than that fix, please file an issue with your ProducerOS version and the
full log.

## Nothing shows up on desktop -- pages look empty

If you're on an old ProducerOS build: an earlier CSS bug hid several list
pages (contributors, rights shares, releases, calendar, LAN devices,
marketing, search results, delivery, backups) entirely on desktop
viewports -- fixed; see the e2e-test commit history for
`src/produceros/web/static/css/app.css`. Update to a current build.

## Browser doesn't open automatically

Some environments block `webbrowser.open()`. Just open
`http://127.0.0.1:8420/` (or your configured port) manually, or pass
`--no-browser` and do so from the start.

## Port already in use

Another process (maybe a previous ProducerOS instance that didn't shut
down cleanly) is using the port. Either close it, or run with a
different port: `ProducerOS.exe run --port 8500`.

## Locked out after failed logins

5 failed attempts locks the account for 60 seconds
(`docs/SECURITY_MODEL.md`). Just wait a minute and try again -- there's no
separate unlock step needed.

## Forgot your password

There's no password-reset flow (single local admin account, no email
integration by design). You'd need to restore from a backup taken before
you forgot it, or -- as a last resort -- delete
`%LOCALAPPDATA%\ProducerOS\produceros.db` to go through first-run setup
again (this discards all your data; restore a backup instead if you have
one -- see `docs/BACKUP_RESTORE.md`).

## LAN mode: phone can't connect

- Confirm both devices are on the **same** Wi-Fi network (not a guest
  network, not phone data).
- Confirm you actually started `run --mode lan` (or
  `.\scripts\run_lan.ps1`), not desktop mode -- desktop mode only binds to
  `127.0.0.1` and is unreachable from another device by design.
- Windows Firewall may prompt to allow `ProducerOS.exe` on first LAN
  launch -- allow it for private networks.
- Pairing codes expire after 10 minutes and are single-use; generate a
  new one if it's stale.

## Scanner reports files as "locked" or unreadable

The file is open in another program (e.g. still being written by FL
Studio's export, or open in a DAW/editor), or you don't have read
permission on it. Re-run the scan once the file is free.

## Restore refuses to run

`restore` requires `--yes` and only accepts a file that passes the
integrity check `restore-dry-run` runs first (`docs/BACKUP_RESTORE.md`).
If the dry-run itself reports `OK: False`, the backup file is corrupt or
not a ProducerOS database -- try a different backup.

## MCP server not reachable

Confirm `mcp_enabled = true` is actually set (see `docs/MCP.md`) --
it's off by default, and simply having `mcp` installed doesn't start it.
Check the startup log for `"Starting local MCP server on ..."`.

## Still stuck

Attach the relevant portion of
`%LOCALAPPDATA%\ProducerOS\logs\produceros.log` (secrets are already
redacted before they're written, so it's safe to share) to a new issue
using the Bug report template.
