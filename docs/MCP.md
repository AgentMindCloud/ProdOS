# MCP Server

ProducerOS includes an optional local [MCP](https://modelcontextprotocol.io)
server so an AI coding/production assistant (Claude, or any MCP-compatible
client) can query your catalog and generate drafts -- read-only and
draft-only, never destructive, never publishing anything, never sending a
message on your behalf. See [ADR 0002](adr/0002-fastmcp-for-mcp-server.md)
for why it's built on FastMCP.

## Enabling it

Off by default. Enable it via `config.toml` in your data directory
(`%LOCALAPPDATA%\ProducerOS\config.toml`):

```toml
[mcp]
enabled = true
bind = "127.0.0.1"
port = 8421
```

or the equivalent environment variables: `PRODUCEROS_MCP_ENABLED=true`,
`PRODUCEROS_MCP_BIND=127.0.0.1`, `PRODUCEROS_MCP_PORT=8421`.

When enabled, `produceros run` starts the MCP server (streamable-HTTP
transport) alongside the web app, bound to localhost by default. Connect
your MCP client to `http://127.0.0.1:8421`.

## Tools

All 14 tools live in `src/produceros/mcp_server/tools.py` and are
registered in `mcp_server/server.py`. Every call runs in its own
short-lived database session and is recorded as an `AuditEvent`
(`event_type="mcp.tool_called"`), same as any other action in the app.

| Tool | Purpose |
|---|---|
| `search_projects` | Search projects by title or internal code |
| `get_project` | Full detail for one project by ID |
| `list_active_projects` | Projects not archived/released/on-hold |
| `list_recent_versions` | Most recently registered asset versions |
| `find_missing_assets` | Asset slots with no current version registered |
| `check_release_readiness` | Re-run the deterministic checklist for a release |
| `list_upcoming_deadlines` | Upcoming, incomplete deadlines within N days |
| `search_catalog_by_mood` | Search projects by mood text |
| `search_catalog_by_bpm` | Search projects within a BPM range |
| `search_catalog_by_key` | Search projects by musical key |
| `get_marketing_plan` | A project's marketing campaigns and drafts |
| `create_marketing_draft` | Generate a new local marketing draft (draft-only, never sent) |
| `create_release_checklist_draft` | Create a draft release and evaluate its checklist (not published) |
| `create_sync_pitch_draft` | Generate a local sync-pitch draft (draft-only, never sent) |

## What it deliberately can't do

No tool deletes, renames, or moves a file; no tool publishes a release,
sends a message, or exposes a secret (the server instructions given to
the MCP client state this explicitly). The two `create_*_draft` tools
generate content the same way the web UI's marketing/checklist features
do -- local, deterministic templates, no external AI call, no invented
facts. `marketing/llm_provider.py` exists as a disabled stub per the
original spec and is never called by anything, including these tools.

## Example: verifying it's running

```powershell
curl http://127.0.0.1:8421/mcp
```

A response (even an error about missing MCP protocol headers, since this
isn't a real MCP client handshake) confirms the server is up. Use an
actual MCP client to call the tools themselves.

## Verified vs. not

Confirmed in this build: the server starts correctly alongside the web
app when enabled (previously it didn't -- `cli.cmd_run` built the whole
server via `mcp_server.build_mcp_server()` but never actually called
`run_mcp_server_blocking()`, a wiring gap now fixed and covered by
`tests/unit/test_cli_run_mcp_wiring.py`), and `tests/unit/test_mcp_schema.py`
verifies the tool schema FastMCP generates matches the expected tool set.
**Not verified**: an actual MCP client (e.g. Claude Desktop/Code)
connecting and calling these tools end-to-end -- that requires a running
MCP client outside this repo's test suite.
