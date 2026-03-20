"""Module for starting the server using FastMCP CLI."""

import asyncio

from fastmcp import FastMCP

from open_targets_platform_mcp.create_server import create_server

mcp: FastMCP = asyncio.run(create_server())
