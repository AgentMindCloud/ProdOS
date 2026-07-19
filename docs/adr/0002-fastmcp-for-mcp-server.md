# ADR 0002: FastMCP for the local MCP server

## Status
Accepted

## Context
The spec calls for an optional, disabled-by-default local MCP server
exposing a fixed set of read/propose-only tools (never direct file
deletes) so an AI coding/production assistant can query ProducerOS's
catalog and release-readiness state. The official `mcp` Python SDK offers
both a low-level `Server` API (manual JSON-RPC method registration, manual
JSON Schema authoring per tool) and a high-level `FastMCP` API
(`@mcp.tool()` decorators that derive the JSON Schema from the Python
function signature).

## Decision
Use `mcp.server.fastmcp.FastMCP`. Tools are plain async functions with
type-hinted parameters; FastMCP introspects the signature to build the
JSON Schema automatically, which keeps a 14-tool surface (see
`docs/MCP.md`) maintainable without hand-written schema duplication that
would drift from the actual function signatures over time.

One consequence of this choice needed a workaround: every tool function
takes a SQLAlchemy `Session` as its first parameter (injected by a
`_audited()` decorator that opens a session, runs the tool, and logs the
call before returning), but FastMCP's schema builder can't represent a
raw `Session` type as JSON Schema and errors on it. `_audited()` in
`mcp_server/server.py` works around this by manually rewriting the wrapped
function's `__signature__` to drop the injected `session` parameter
before FastMCP sees it, so the schema FastMCP generates matches the
tool's real (session-free) public interface.

## Consequences
- Adding a new tool is "write a typed async function," not "write a
  function and hand-maintain a parallel JSON Schema" -- lower risk of
  schema/implementation drift.
- The `__signature__` rewrite in `_audited()` is a documented, deliberate
  hack tied to a specific FastMCP limitation; if a future FastMCP version
  supports dependency injection or session-hiding natively, that
  workaround should be revisited and likely removed.
- The server binds to localhost only and is off by default
  (`config.toml [mcp] enabled`), independent of this library choice --
  see `docs/SECURITY_MODEL.md`.
