"""Server setup and configuration for OpenTargets MCP."""

import base64
from importlib import resources

from fastmcp import FastMCP
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from mcp.types import Icon

from open_targets_platform_mcp.settings import settings
from open_targets_platform_mcp.tools import (
    batch_query_with_jq,
    batch_query_without_jq,
    get_open_targets_graphql_schema,
    query_with_jq,
    query_without_jq,
    search_entities,
)


def create_server() -> FastMCP:
    """Set up the MCP server and register all tools.

    This function registers tools based on current configuration.

    Returns:
        FastMCP: Configured MCP server instance with all tools registered
    """
    favicon_bytes = resources.files("open_targets_platform_mcp.static").joinpath("favicon.png").read_bytes()
    data_uri = f"data:image/png;base64,{base64.b64encode(favicon_bytes).decode('utf-8')}"
    mcp = FastMCP(
        name=settings.server_name,
        icons=[Icon(src=data_uri, mimeType="image/png")],
    )

    mcp.add_middleware(ErrorHandlingMiddleware())

    mcp.tool(get_open_targets_graphql_schema)
    mcp.tool(
        search_entities,
        description=resources.files("open_targets_platform_mcp.tools.search_entities")
        .joinpath("description.txt")
        .read_text(encoding="utf-8"),
    )

    if settings.jq_enabled:
        mcp.tool(
            query_with_jq,
            description=resources.files("open_targets_platform_mcp.tools.query")
            .joinpath("with_jq_description.txt")
            .read_text(encoding="utf-8"),
        )
        mcp.tool(
            batch_query_with_jq,
            description=resources.files("open_targets_platform_mcp.tools.batch_query")
            .joinpath("with_jq_description.txt")
            .read_text(encoding="utf-8"),
        )
    else:
        mcp.tool(
            query_without_jq,
            description=resources.files("open_targets_platform_mcp.tools.query")
            .joinpath("without_jq_description.txt")
            .read_text(encoding="utf-8"),
        )
        mcp.tool(
            batch_query_without_jq,
            description=resources.files("open_targets_platform_mcp.tools.batch_query")
            .joinpath("without_jq_description.txt")
            .read_text(encoding="utf-8"),
        )

    return mcp
