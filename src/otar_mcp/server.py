"""Server setup and configuration for OpenTargets MCP."""

from fastmcp import FastMCP

from otar_mcp.mcp_instance import mcp

# Import tool modules to register them with the MCP instance
# These imports trigger the @mcp.tool() decorators
from otar_mcp.tools import batch_query, examples, query, schema, search, search_entity, semantic_search  # noqa: F401


def setup_server() -> FastMCP:
    """
    Set up the MCP server with all tools.

    Returns:
        FastMCP: Configured MCP server instance with all tools registered
    """
    return mcp
