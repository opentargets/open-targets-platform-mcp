"""Central MCP instance for the OpenTargets MCP server."""

from fastmcp import FastMCP

from otar_mcp.config import config

# Create the MCP server instance
mcp = FastMCP(config.server_name)
