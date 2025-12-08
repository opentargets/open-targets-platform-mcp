"""Command-line interface for OpenTargets MCP server."""

import asyncio
from importlib import metadata
from typing import Annotated

import typer

from platform_mcp.config import config

app = typer.Typer()


def _version_callback(value: bool) -> bool:
    """Display the installed package version and exit when requested."""
    if value:
        package_version = metadata.version("platform-mcp")
        typer.echo(f"otpmcp {package_version}")
        raise typer.Exit
    return value


@app.callback()
def root(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the package version and exit.",
        ),
    ],
) -> None:
    """OpenTargets MCP - Model Context Protocol server for OpenTargets Platform API."""


@app.command(name="serve-http")
def serve_http(
    host: str = typer.Option(
        config.http_host,
        help="Host to bind the HTTP server to",
        show_default=True,
    ),
    port: int = typer.Option(
        config.http_port,
        help="Port to bind the HTTP server to",
        show_default=True,
    ),
    jq: bool = typer.Option(
        False,
        "--jq/--no-jq",
        help="Enable jq filtering support for query tools",
        show_default=True,
    ),
) -> None:
    """Start the MCP server with HTTP transport.

    This mode is useful for testing and development, or when you need to
    access the MCP server over HTTP.
    """
    # Set jq configuration BEFORE importing server
    config.jq_enabled = jq

    # Now import and setup server (triggers tool registration)
    from platform_mcp.server import setup_server

    mcp = setup_server()

    jq_status = "enabled" if jq else "disabled"
    typer.echo(f"Starting OpenTargets MCP server on http://{host}:{port}/mcp (jq filtering: {jq_status})")
    mcp.run(transport="http", host=host, port=port)


@app.command(name="serve-stdio")
def serve_stdio(
    jq: bool = typer.Option(
        False,
        "--jq/--no-jq",
        help="Enable jq filtering support for query tools",
        show_default=True,
    ),
) -> None:
    """Start the MCP server with stdio transport.

    This is the standard transport for MCP servers and is used by
    Claude Desktop and other MCP clients.
    """
    # Set jq configuration BEFORE importing server
    config.jq_enabled = jq

    # Now import and setup server (triggers tool registration)
    from platform_mcp.server import setup_server

    mcp = setup_server()

    jq_status = "enabled" if jq else "disabled"
    typer.echo(
        f"Starting OpenTargets MCP server with stdio transport (jq filtering: {jq_status})",
        err=True,
    )
    mcp.run(transport="stdio")


@app.command(name="list-tools")
def list_tools(
    jq: bool = typer.Option(
        False,
        "--jq/--no-jq",
        help="Show tools as they would appear with/without jq support",
        show_default=True,
    ),
) -> None:
    """List all available MCP tools."""
    # Set jq configuration to show appropriate tool signatures
    config.jq_enabled = jq

    from platform_mcp.server import setup_server

    mcp = setup_server()

    jq_status = "with jq support" if jq else "without jq support"
    typer.echo(f"Available tools ({jq_status}):")

    # Dynamically list all registered tools using public API
    tools = asyncio.run(mcp.get_tools())
    for name, tool in tools.items():
        # Extract first line of description from the tool's description field
        description = tool.description or "No description available"
        first_line = description.split("\n")[0].strip()
        typer.echo(f"  - {name}: {first_line}")


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
