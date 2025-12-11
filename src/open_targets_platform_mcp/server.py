"""Module for starting the server using FastMCP CLI."""

from fastmcp import FastMCP

from open_targets_platform_mcp.create_server import create_server

mcp: FastMCP = create_server()
