import asyncio

from produceros.mcp_server.server import build_mcp_server

EXPECTED_TOOLS = {
    "search_projects",
    "get_project",
    "list_active_projects",
    "list_recent_versions",
    "find_missing_assets",
    "check_release_readiness",
    "list_upcoming_deadlines",
    "search_catalog_by_mood",
    "search_catalog_by_bpm",
    "search_catalog_by_key",
    "get_marketing_plan",
    "create_marketing_draft",
    "create_release_checklist_draft",
    "create_sync_pitch_draft",
}


def test_all_required_tools_are_registered():
    server = build_mcp_server()
    tools = asyncio.run(server.list_tools())
    tool_names = {t.name for t in tools}
    assert tool_names >= EXPECTED_TOOLS


def test_tool_schemas_have_no_session_parameter():
    server = build_mcp_server()
    tools = asyncio.run(server.list_tools())
    for tool in tools:
        properties = tool.inputSchema.get("properties", {})
        assert (
            "session" not in properties
        ), f"{tool.name} leaked its session parameter into the MCP schema"


def test_tool_schemas_are_valid_json_schema_objects():
    server = build_mcp_server()
    tools = asyncio.run(server.list_tools())
    for tool in tools:
        assert tool.inputSchema.get("type") == "object"
        assert isinstance(tool.description, str) and tool.description
