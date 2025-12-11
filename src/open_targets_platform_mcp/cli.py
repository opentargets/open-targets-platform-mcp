import asyncio
from importlib import metadata
from typing import Annotated

import typer

from open_targets_platform_mcp.create_server import create_server
from open_targets_platform_mcp.settings import TransportType, settings

PACKAGE_NAME = "open_targets_platform_mcp"
PACKAGE_VERSION = metadata.version(PACKAGE_NAME)

app = typer.Typer(
    help=f"Model Context Protocol server for Open Targets Platform version {PACKAGE_VERSION}",
)


def _version_callback(value: bool) -> None:
    """Show the package version and exit."""
    if value:
        typer.echo(f"{PACKAGE_NAME} {PACKAGE_VERSION}")
        raise typer.Exit


def _list_tools_callback(value: bool) -> None:
    """List all available MCP tools."""
    if value:
        mcp = create_server()
        tools = asyncio.run(mcp.get_tools())
        for name, tool in tools.items():
            # Extract first line of description from the tool's description field
            description = tool.description or "No description available"
            first_line = description.split("\n")[0].strip()
            typer.echo(f"  - {name}: {first_line}")
        raise typer.Exit


@app.callback(invoke_without_command=True)
def root(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            help=_version_callback.__doc__,
            is_eager=True,
            callback=_version_callback,
        ),
    ] = None,
    list_tools: Annotated[
        bool | None,
        typer.Option(
            "--list-tools",
            help=_list_tools_callback.__doc__,
            is_eager=True,
            callback=_list_tools_callback,
        ),
    ] = None,
    server_name: Annotated[
        str | None,
        typer.Option(
            "--name",
            help="Name of the server",
            show_default=True,
        ),
    ] = settings.server_name,
    transport: Annotated[
        TransportType | None,
        typer.Option(
            help="Protocol the server to use",
            show_default=True,
        ),
    ] = settings.transport,
    http_host: Annotated[
        str | None,
        typer.Option(
            "--host",
            help="Host to bind the HTTP server to",
            show_default=True,
        ),
    ] = settings.http_host,
    http_port: Annotated[
        int | None,
        typer.Option(
            "--port",
            help="Port to bind the HTTP server to",
            show_default=True,
        ),
    ] = settings.http_port,
    jq_enabled: Annotated[
        bool | None,
        typer.Option(
            "--jq",
            help="Enable jq filtering support for query tools",
            show_default=True,
        ),
    ] = settings.jq_enabled,
    api_endpoint: Annotated[
        str | None,
        typer.Option(
            "--api",
            help="Open Targets Platform API endpoint to use",
            show_default=True,
        ),
    ] = str(settings.api_endpoint),
    api_call_timeout: Annotated[
        int | None,
        typer.Option(
            "--timeout",
            help="Request timeout (in seconds) for calls to the Open Targets Platform API.",
            show_default=True,
        ),
    ] = settings.api_call_timeout,
) -> None:
    """Entry point of CLI."""
    settings.update(**locals())

    mcp = create_server()

    try:
        if settings.transport == TransportType.HTTP:
            mcp.run(
                transport=settings.transport.value,
                host=settings.http_host,
                port=settings.http_port,
            )
        else:
            mcp.run(
                transport=settings.transport.value,
            )
    except KeyboardInterrupt:
        pass
    except asyncio.CancelledError:
        pass


def main() -> None:
    """Entry point of the application."""
    app()


if __name__ == "__main__":
    main()
