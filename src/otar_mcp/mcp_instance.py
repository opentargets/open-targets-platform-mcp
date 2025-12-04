"""Central MCP instance for the OpenTargets MCP server."""

from fastmcp import FastMCP
from mcp.types import Icon

from otar_mcp.config import config

# Create the MCP server instance
mcp = FastMCP(
    config.server_name,
    icons=[
        Icon(
            src="https://raw.githubusercontent.com/opentargets/ot-ui-apps/main/apps/platform/public/favicon.png",
            mimeType="image/png",
        )
    ],
)
