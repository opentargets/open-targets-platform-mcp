"""Tool for fetching the OpenTargets GraphQL schema."""

from graphql import print_schema

from otar_mcp.client import fetch_graphql_schema
from otar_mcp.config import config
from otar_mcp.mcp_instance import mcp


@mcp.tool(name="get_open_targets_graphql_schema")
def get_open_targets_graphql_schema() -> dict:
    """Retrieve the Open Targets GraphQL schema for query construction.

    Returns:
        dict: Schema string in format {'schema': '...'} containing GraphQL type definitions or error message.
    """
    try:
        schema = fetch_graphql_schema(config.api_endpoint)
        return {"schema": print_schema(schema)}
    except Exception as e:
        return {"error": f"Failed to fetch Open Targets GraphQL schema: {e!s}"}
