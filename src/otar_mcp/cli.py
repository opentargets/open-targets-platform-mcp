"""Command-line interface for OpenTargets MCP server."""

import asyncio

import click

from otar_mcp.config import config
from otar_mcp.server import setup_server


@click.group()
@click.version_option()
def cli() -> None:
    """OpenTargets MCP - Model Context Protocol server for OpenTargets Platform API."""
    pass


@cli.command(name="serve-http")
@click.option(
    "--host",
    default=config.http_host,
    help="Host to bind the HTTP server to",
    show_default=True,
)
@click.option(
    "--port",
    default=config.http_port,
    help="Port to bind the HTTP server to",
    show_default=True,
)
def serve_http(host: str, port: int) -> None:
    """Start the MCP server with HTTP transport.

    This mode is useful for testing and development, or when you need to
    access the MCP server over HTTP.
    """
    mcp = setup_server()
    click.echo(f"Starting OpenTargets MCP server on http://{host}:{port}/mcp")
    mcp.run(transport="http", host=host, port=port)


@cli.command(name="serve-stdio")
def serve_stdio() -> None:
    """Start the MCP server with stdio transport.

    This is the standard transport for MCP servers and is used by
    Claude Desktop and other MCP clients.
    """
    mcp = setup_server()
    click.echo("Starting OpenTargets MCP server with stdio transport", err=True)
    mcp.run(transport="stdio")


@cli.command(name="list-tools")
def list_tools() -> None:
    """List all available MCP tools."""
    mcp = setup_server()  # Ensure tools are registered
    click.echo("Available tools:")

    # Dynamically list all registered tools using public API
    tools = asyncio.run(mcp.get_tools())
    for name, tool in tools.items():
        # Extract first line of description from the tool's description field
        description = tool.description or "No description available"
        first_line = description.split("\n")[0].strip()
        click.echo(f"  - {name}: {first_line}")


def main() -> None:
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
