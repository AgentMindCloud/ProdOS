# Backup & Restore

## Creating a backup

Three equivalent ways:
- Backup page in the app -> **Create backup**.
- `ProducerOS.exe backup-create` (or `.\scripts\backup.ps1`).

A backup is a full copy of your SQLite database, taken via SQLite's
online backup API (`services/backup.create_backup`, using
`sqlite3.Connection.backup()`), so it's safe to run while the app is
live -- no need to stop ProducerOS first. Backups are written to
`%LOCALAPPDATA%\ProducerOS\backups\`, named
`produceros_<UTC timestamp>.db`, and every backup is checksummed
(SHA-256) at creation time.

**Backups only cover the database** -- your actual audio files are never
copied (ProducerOS never duplicates your music). If you want your source
files backed up too, use your normal file-backup tool on your music
folders; ProducerOS's backup is metadata only (projects, versions,
rights, releases, etc., not the `.wav`/`.flp` files themselves).

Consider scheduling `scripts\backup.ps1` (e.g. via Windows Task
Scheduler, daily) in addition to backing up before anything risky like an
upgrade or a restore.

## Verifying a backup

Backup page -> **Verify** next to a backup, or it's checked automatically
as part of `restore-dry-run` below. Verification runs SQLite's
`PRAGMA integrity_check` against the backup file and confirms it's a
readable, non-corrupt database.

## Restoring

Restoring is destructive (it replaces your live database), so it always
requires an explicit preview and confirmation step:

**From the command line:**
```powershell
.\scripts\restore.ps1 -BackupPath "$env:LOCALAPPDATA\ProducerOS\backups\produceros_20260101T000000Z.db"
```
This runs a dry-run preview first (integrity check + row counts per
table), then asks you to type `RESTORE` (all caps) before doing anything.

**Directly via the CLI** (what the script wraps):
```powershell
ProducerOS.exe restore-dry-run "<path>"   # preview only, makes no changes
ProducerOS.exe restore "<path>" --yes     # actually restores
```
`restore` without `--yes` refuses to run and tells you to dry-run first
-- there's no way to restore accidentally from the command line.

**From the web UI:** Backup page -> pick a backup -> the dry-run preview
appears, then confirm to restore.

### What happens during a restore

`services/backup.restore_backup` always takes a **pre-restore safety
copy** of your current live database before overwriting it -- so if you
restore the wrong backup, you can restore again from that safety copy.
It refuses to run against anything that isn't a valid SQLite database
(caught by the same integrity check the dry-run shows you) --
`tests/integration/test_backup_and_restore.py` covers a corrupt-backup
case explicitly.

## Exporting data

Beyond binary backups, the Backup page also offers two export formats for
inspecting or migrating your data outside ProducerOS entirely:
- **Metadata export** (`/backup/export/metadata.json`) -- your full
  catalog as JSON.
- **Audio manifest export** (`/backup/export/audio-manifest.json`) -- a
  list of every registered asset version and its recorded path/checksum,
  useful for cross-checking against your actual files on disk.

## Restoring onto a different machine

Since the database has no hardcoded paths to the install location (only
to your registered file paths, which you'd need to still have at the same
locations, or re-register), you can copy a backup `.db` file to a new
Windows machine, run `ProducerOS.exe restore "<path>" --yes` against a
fresh install's data directory, and continue from there.
