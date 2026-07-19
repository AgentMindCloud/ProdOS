# ADR 0004: SQLite-only runtime, PostgreSQL-compatible models

## Status
Accepted

## Context
ProducerOS is a local-first, single-user desktop tool: the spec requires
it to run with zero external services and no Docker, which rules out
Postgres as the *default* database. At the same time, the data model
should not accidentally paint the project into a SQLite-only corner if a
future multi-user/hosted variant is ever wanted.

## Decision
The only database ProducerOS runs against is SQLite, opened in WAL mode
by default for better read concurrency between the web app and the
scanner (`db/session._build_engine`). All models are written with
dialect-agnostic SQLAlchemy types (`Uuid`, not a Postgres-specific UUID
type; a custom `UTCDateTime` TypeDecorator over `DateTime(timezone=True)`,
not a raw column) so the same model definitions are valid against
PostgreSQL without changes, even though nothing in the runtime currently
connects to one.

The `UTCDateTime` type (`db/base.py`) exists specifically because of a
SQLite gap: SQLite has no native timezone-aware datetime type, so a plain
`DateTime(timezone=True)` column silently returns a naive `datetime` on
read-back, which then crashes any comparison against
`datetime.now(timezone.utc)` (this was an actual bug, caught by
`tests/security/test_auth_security.py`'s brute-force lockout test:
`user.locked_until` came back naive after a session-commit reload and
blew up the `>` comparison). `UTCDateTime` always stores naive UTC and
always returns UTC-aware values, working identically on SQLite and
Postgres.

## Consequences
- No `psycopg`/Postgres driver dependency in the default install --
  keeps the zero-external-services requirement intact.
- If ProducerOS is ever pointed at Postgres, the model layer needs no
  changes; only `config.Settings.database_url` and the connection
  bootstrap in `db/session.py` (which special-cases `sqlite://` pragmas)
  would need a Postgres branch.
- Every timestamp column must use `UTCDateTime`, not
  `DateTime(timezone=True)` directly -- documented in `db/base.py` and
  enforced by convention (there is no lint rule for it; a code reviewer
  needs to catch a raw `DateTime(timezone=True)` slipping back in).
