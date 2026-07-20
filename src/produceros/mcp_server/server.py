"""Local MCP server (spec section 21).

Disabled by default (``config.toml [mcp] enabled = false``), bound to
localhost, and requires no external API. Every tool call is wrapped so it
runs inside its own short-lived database session and is recorded in the
audit log, matching the same audit trail every other ProducerOS action
produces. ProducerOS's web application is fully functional with this
server never started.
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from typing import Any

from produceros.config import get_settings
from produceros.db.session import session_scope
from produceros.logging_config import get_logger
from produceros.mcp_server import tools as t
from produceros.services.audit import log_event

logger = get_logger("mcp")


def is_mcp_enabled() -> bool:
    return get_settings().mcp_enabled


def _audited(tool_name: str, fn: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap a ``fn(session, ...)`` tool implementation so MCP sees a
    ``(...)`` signature with ``session`` removed (it's supplied
    internally, per call, and must never appear in the tool's schema)."""

    @functools.wraps(fn)
    def wrapper(**kwargs: Any) -> Any:
        with session_scope() as session:
            result = fn(session, **kwargs)
            log_event(
                session,
                event_type="mcp.tool_called",
                summary=f"MCP tool '{tool_name}' called.",
                metadata={"tool": tool_name, "args": {k: str(v) for k, v in kwargs.items()}},
            )
            return result

    original_params = list(inspect.signature(fn).parameters.values())[1:]  # drop `session`
    # Deliberate: FastMCP builds the tool's JSON Schema from __signature__,
    # and the injected Session must not appear in it (see ADR 0002).
    wrapper.__signature__ = inspect.Signature(parameters=original_params)  # type: ignore[attr-defined]
    wrapper.__name__ = tool_name
    return wrapper


def build_mcp_server():
    """Construct the FastMCP application. Import is local so the ``mcp``
    package is only required when MCP is actually enabled and started."""
    from mcp.server.fastmcp import FastMCP

    settings = get_settings()
    mcp = FastMCP(
        name="ProducerOS",
        instructions=(
            "Read-only and draft-only tools over a local ProducerOS catalog. "
            "No tool here deletes files, publishes releases, sends messages, "
            "or exposes secrets."
        ),
        host=settings.mcp_bind,
        port=settings.mcp_port,
    )

    mcp.add_tool(
        _audited("search_projects", t.search_projects),
        name="search_projects",
        description="Search projects by title or internal code.",
    )
    mcp.add_tool(
        _audited("get_project", t.get_project),
        name="get_project",
        description="Get full detail for one project by ID.",
    )
    mcp.add_tool(
        _audited("list_active_projects", t.list_active_projects),
        name="list_active_projects",
        description="List all projects not archived/released/on-hold.",
    )
    mcp.add_tool(
        _audited("list_recent_versions", t.list_recent_versions),
        name="list_recent_versions",
        description="List the most recently registered asset versions.",
    )
    mcp.add_tool(
        _audited("find_missing_assets", t.find_missing_assets),
        name="find_missing_assets",
        description="Find asset slots with no current version registered.",
    )
    mcp.add_tool(
        _audited("check_release_readiness", t.check_release_readiness),
        name="check_release_readiness",
        description="Re-run the deterministic release-readiness checklist for a release.",
    )
    mcp.add_tool(
        _audited("list_upcoming_deadlines", t.list_upcoming_deadlines),
        name="list_upcoming_deadlines",
        description="List upcoming, incomplete deadlines within N days.",
    )
    mcp.add_tool(
        _audited("search_catalog_by_mood", t.search_catalog_by_mood),
        name="search_catalog_by_mood",
        description="Search projects by mood text.",
    )
    mcp.add_tool(
        _audited("search_catalog_by_bpm", t.search_catalog_by_bpm),
        name="search_catalog_by_bpm",
        description="Search projects within a BPM range.",
    )
    mcp.add_tool(
        _audited("search_catalog_by_key", t.search_catalog_by_key),
        name="search_catalog_by_key",
        description="Search projects by musical key.",
    )
    mcp.add_tool(
        _audited("get_marketing_plan", t.get_marketing_plan),
        name="get_marketing_plan",
        description="Get a project's marketing campaigns and drafts.",
    )
    mcp.add_tool(
        _audited("create_marketing_draft", t.create_marketing_draft),
        name="create_marketing_draft",
        description="Generate a new local marketing draft for a project (draft-only, never sent).",
    )
    mcp.add_tool(
        _audited("create_release_checklist_draft", t.create_release_checklist_draft),
        name="create_release_checklist_draft",
        description="Create a draft release and run its readiness checklist (draft-only, not published).",
    )
    mcp.add_tool(
        _audited("create_sync_pitch_draft", t.create_sync_pitch_draft),
        name="create_sync_pitch_draft",
        description="Generate a local sync-pitch draft for a project (draft-only, never sent).",
    )

    return mcp


def run_mcp_server_blocking() -> None:
    """Entry point used by the CLI when MCP is enabled. Blocks the calling
    thread/process -- callers should run this in its own thread/process."""
    if not is_mcp_enabled():
        logger.info("MCP server is disabled (config.toml [mcp] enabled = false); not starting.")
        return
    server = build_mcp_server()
    logger.info(
        "Starting local MCP server on %s:%s", get_settings().mcp_bind, get_settings().mcp_port
    )
    server.run(transport="streamable-http")
