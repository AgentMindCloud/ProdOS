# ADR 0001: Plain `Uuid` columns instead of a circular FK for "current version" pointers

## Status
Accepted

## Context
Several entities need a "current version" pointer: `Project.current_mix_asset_version_id`
points at an `AssetVersion`, and an `Asset`'s "current version" pointer works
the same way. `AssetVersion` in turn belongs to `Asset`, which belongs to
`Project`. Expressing the "current version" pointer as a real foreign key
back onto `AssetVersion` creates a three-table circular FK dependency:
`Project -> AssetVersion -> Asset -> Project`.

SQLite can create the tables (it doesn't validate FK targets exist at
`CREATE TABLE` time), but the cycle breaks two things that matter in
practice: Alembic's autogenerate can't order `CREATE TABLE` statements for
a true cycle without deferred constraints, and naive fixture/demo-data
insertion order breaks because there is no topological order that
satisfies all three FKs at once (every insert order leaves one row
pointing at a not-yet-inserted row).

## Decision
`Project.current_mix_asset_version_id` and the `Asset` "current version"
pointer are declared as plain `Uuid` columns (via SQLAlchemy's
dialect-agnostic `Uuid` type), **not** wrapped in `ForeignKey(...)`. The
application layer (`services/assets.set_current_version`) is the sole
place that ever writes these columns, and it always writes an ID that was
just validated to belong to the correct `Asset`/`Project`. Reads join
through `session.get()` rather than relying on ORM-declared relationships
for these two pointers.

This is documented inline in `models/catalog.py` and `models/assets.py`
next to the fields themselves, not just here.

## Consequences
- No database-level guarantee that the pointer targets a real row of the
  right type. Correctness is enforced entirely by the service layer.
- Demo data generation, migrations, and tests can insert rows in a normal
  parent-before-child order without deferred-constraint tricks.
- If ProducerOS ever moves to PostgreSQL (see ADR 0004), the same
  decision holds: Postgres supports deferrable FKs, but adding one here
  only to satisfy referential integrity on a value the app already fully
  controls isn't worth the migration complexity for a single-user local
  tool.
