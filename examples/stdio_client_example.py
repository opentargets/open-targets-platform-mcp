"""Example of using OpenTargets MCP with stdio transport.

This example demonstrates how to use the OpenTargets MCP server
with stdio transport, which is the standard for Claude Desktop integration.
"""

import asyncio

from fastmcp import Client


async def main() -> None:
    """Demonstrate basic usage of OpenTargets MCP tools via stdio."""
    # For stdio transport, you would typically configure this in Claude Desktop
    # or another MCP client. This example shows the structure.

    # In Claude Desktop config, you would add:
    # {
    #   "mcpServers": {
    #     "opentargets": {
    #       "command": "uv",
    #       "args": ["run", "otar-mcp", "serve-stdio"]
    #     }
    #   }
    # }

    print("For stdio transport, configure this in your MCP client (e.g., Claude Desktop)")
    print("See README.md for configuration instructions")


if __name__ == "__main__":
    asyncio.run(main())
