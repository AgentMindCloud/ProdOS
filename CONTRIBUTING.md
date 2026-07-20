# Contributing

Before anything else, read `AGENTS.md` -- it holds the non-negotiable
product constraints (no external services, never touch music files
without approval, no invented marketing content, etc.). A change that
violates those doesn't get merged regardless of code quality.

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Windows shortcut: `.\scripts\setup_windows.ps1`.

## Development loop

```bash
python -m produceros.cli run --no-browser   # run the app locally
pytest tests/unit tests/integration tests/security -q
pytest tests/e2e -q                          # needs Playwright Chromium
ruff format src tests && ruff check src tests
mypy src
```

`.\scripts\run_tests.ps1` runs the same sequence on Windows. CI
(`.github/workflows/ci.yml`) runs all of it on Ubuntu and Windows, plus
`alembic check` and a demo-data round trip -- anything red there blocks
merge.

## Conventions

- Business logic lives in `services/` (or a domain package), not in
  routes. Routes parse, verify CSRF, call one service, redirect. See
  `ARCHITECTURE.md` for the layering rules and the CSRF-middleware
  pattern every new form route must follow.
- Every state-changing service call logs an `AuditEvent`.
- New datetime columns use `UTCDateTime` from `db/base.py`, never raw
  `DateTime(timezone=True)` (ADR 0004 explains the SQLite bug this
  prevents).
- Schema changes: edit the models, generate a migration
  (`alembic revision --autogenerate`), and confirm `alembic check` is
  clean. Never edit an already-committed migration.
- Filename-matching regexes use `(?<![A-Za-z0-9])` / `(?![A-Za-z0-9])`
  lookarounds, not `\b` -- underscores are word characters, so `\b`
  silently fails next to them (this was a real shipped bug).
- Tests use the isolated-data-dir fixtures from `tests/conftest.py`; a
  test must never read or write a real ProducerOS data directory.
- Suppressions (`# noqa`, `# nosec`, waived checklist rules) always carry
  a one-line justification.

## Commits and PRs

- One commit per coherent phase of work, with a message that explains
  *why* (including any bugs found along the way and how they were
  caught).
- Fill in the PR template checklist honestly -- especially the "tests
  actually run" boxes. Never claim a test passed without running it.
- Docs are part of the change: behavior changes update the relevant
  `docs/*.md`, `CHANGELOG.md`, and -- if project state shifts --
  `HANDOFF.md`.

## Reporting security issues

See `SECURITY.md`.
