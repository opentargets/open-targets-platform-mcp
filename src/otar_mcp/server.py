"""Server setup and configuration for OpenTargets MCP."""

from fastmcp import FastMCP

from otar_mcp.config import config

# Create the MCP server instance
mcp = FastMCP(config.server_name)


def setup_server() -> FastMCP:
    """
    Set up the MCP server with all tools.

    This function imports all tool modules to ensure they are registered
    with the MCP instance via their @mcp.tool() decorators.

    Returns:
        FastMCP: Configured MCP server instance
    """
    # Import tool modules to register them with the MCP instance
    # These imports trigger the @mcp.tool() decorators
    from otar_mcp.tools import examples, query, schema  # noqa: F401

    return mcp
