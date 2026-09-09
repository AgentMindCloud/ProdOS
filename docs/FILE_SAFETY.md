# Music file safety

The owner's rule for 0.2.1 is: **approved moves and renames are allowed;
deleting or overwriting user files is never an available operation.**

- Scanning, registration and playback read local files. They do not upload,
  rename, move, overwrite or delete music.
- Delete and replace operations are refused, including previously approved
  operations. No confirmation or configuration option enables them.
- Move/rename still requires explicit approval and a destination that does not
  exist. Existing files, directories and broken links cause refusal. A safe
  native rename must be available; cross-filesystem moves do not fall back to
  copying and deleting the source. Use the operating system's file manager when
  the app refuses an unsupported move.
- File-operation services are internal capabilities; this patch does not add
  move/rename controls to the UI or MCP.
- Delivery exports still require a manifest and approval. They need a **new**
  output directory. Every copied file and the manifest are created exclusively;
  existing destinations and unsafe paths are rejected. A failed partial export
  is retained for inspection instead of deleting files as cleanup.
- Demo data uses unique folders and exclusive file creation. Demo cleanup removes
  only the app's demo database records and leaves files on disk. It does not scan
  unrelated selected folders or remove user-owned analytics records.
- ProducerOS must write its own local database, settings, logs and backups to
  work. Confirmed restore replaces only its own validated app database. Linked
  app-storage paths are rejected, new snapshots are created exclusively and
  restore uses a unique temporary filename instead of overwriting a fixed path.

The public website is separate: it has a synthetic demo and downloads, with no
folder picker, file-management API, or connection to the local desktop server.

These are application-level controls verified using isolated regression tests.
ProducerOS is an ordinary desktop process, not an operating-system sandbox.
They do not justify an absolute guarantee against compromised software, hostile
local processes racing filesystem changes, or every future defect. Back up music
separately; app metadata backups do not include audio.

The previously published 0.2.0 binary does not gain these protections when source
code changes. Users need the updated 0.2.1 build. Publication status and current
verification evidence are recorded in `HANDOFF.md`.
