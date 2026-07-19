# ADR 0005: PyInstaller onedir build, resolved via `sys._MEIPASS` when frozen

## Status
Accepted

## Context
ProducerOS ships as a standalone Windows executable via PyInstaller so a
producer never installs Python. PyInstaller offers two build modes:
**onefile** (a single `.exe` that self-extracts to a temp directory on
every launch) and **onedir** (a folder with the `.exe` plus an
`_internal\` directory holding the Python runtime and bundled data
files). The app also needs to find its bundled `alembic.ini` and
`migrations/` at runtime to self-migrate its database
(`cli._alembic_config`).

## Decision
Build **onedir** (`packaging/pyinstaller/produceros.spec`): faster
startup than onefile's per-launch extraction, and easier to inspect/debug
during development. `cli._alembic_config()` locates the bundled
`alembic.ini` via `sys._MEIPASS` when `sys.frozen` is set, not by assuming
it sits next to the executable.

That "next to the executable" assumption was the initial (wrong)
implementation, and it broke in a real smoke test of the built binary:
PyInstaller 6's onedir layout puts every bundled `datas` entry under
`_internal\`, not flat next to the `.exe`, so `Path(sys.argv[0]).parent /
"alembic.ini"` pointed at a file that doesn't exist there, and
`db-upgrade` failed with `alembic.util.exc.CommandError: Path doesn't
exist`. `sys._MEIPASS` is PyInstaller's own extraction-root variable and
resolves correctly for both onedir (`_internal\`) and onefile (the
per-launch temp dir), so using it instead of a hand-rolled relative-path
guess is also forward-compatible if the build mode ever changes.

## Consequences
- Distributing the app means shipping the whole `dist\ProducerOS\` folder
  (`.exe` + `_internal\`), not the `.exe` alone -- documented in
  `packaging/README.md` and reflected in `windows-build.yml`'s
  `Compress-Archive -Path dist\ProducerOS\*`.
- `cli._alembic_config()` has two branches (`sys.frozen` vs. not); the
  non-frozen branch still resolves `alembic.ini` from the source tree for
  local development, unchanged.
- This bug was caught only by actually running the built binary
  end-to-end (`produceros run`, watching migrations apply and the server
  respond to a real HTTP request) -- a successful `pyinstaller` build
  alone did not surface it. `windows-build.yml`'s smoke-test step exists
  specifically to keep catching this class of bug in CI, not just in an
  ad hoc local build.
