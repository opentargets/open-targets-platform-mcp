"""Tool for fetching the OpenTargets GraphQL schema."""

from graphql import print_schema

from otar_mcp.client import fetch_graphql_schema
from otar_mcp.config import config
from otar_mcp.server import mcp


@mcp.tool()
def get_open_targets_graphql_schema() -> dict:
    """Fetch the Open Targets GraphQL schema.

    Returns the complete GraphQL schema for the OpenTargets Platform API,
    which can be used to understand available queries, types, and fields.

    Returns:
        dict: Schema as a string in the GraphQL SDL format, or error information
    """
    try:
        schema = fetch_graphql_schema(config.api_endpoint)
        return {"schema": print_schema(schema)}
    except Exception as e:
        return {"error": f"Failed to fetch Open Targets GraphQL schema: {e!s}"}
