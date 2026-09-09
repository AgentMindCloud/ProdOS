# ADR 0008: No deletion or overwriting of user files

- Date: 2026-09-10
- Status: implemented in 0.2.1; publication/verification status in HANDOFF.md

The owner clarified that explicit approval may permit moving/renaming, but must
never permit deleting or overwriting user files. This supersedes the earlier
specification's approval-based deletion allowance without disabling read access
needed for scanning/playback.

DELETE and REPLACE are refused, including stored approvals. Copies/exports use
exclusive creation. Moves use native no-replace operations and refuse unsupported
or cross-device cases rather than falling back to copy-delete. No new UI/MCP
file-management controls are added.

Demo cleanup affects database rows only. Demo files are uniquely created and
retained. Export folders must be new; partial failures leave new output in place.
The app still maintains its own metadata database/settings/logs/backups. Writable
aliases and staging collisions are guarded. External SQLite backup inspection
uses immutable standalone reads because ordinary read-only connections can modify
WAL sidecars; backups with pending WAL data are rejected rather than silently
ignoring transactions.

The public website remains a separate demo/download site with no folder-access
API. This is an application-level contract, not OS-enforced confinement against
compromised code or adversarial local filesystem races. Existing 0.2.0 downloads
do not change automatically; the stronger behavior requires the new build.
