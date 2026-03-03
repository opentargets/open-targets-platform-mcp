"""Server setup and configuration for Open Targets Platform MCP."""

import base64
from importlib import resources

from fastmcp import FastMCP
from graphql import print_schema
from mcp.types import Icon

from open_targets_platform_mcp.cache import cache
from open_targets_platform_mcp.client.graphql import fetch_graphql_schema
from open_targets_platform_mcp.middleware import AdaptiveRateLimitingMiddleware
from open_targets_platform_mcp.settings import settings
from open_targets_platform_mcp.tools import (
    batch_query_with_jq,
    batch_query_without_jq,
    get_open_targets_graphql_schema,
    get_type_dependencies,
    query_with_jq,
    query_without_jq,
    search_entities,
)
from open_targets_platform_mcp.tools.schema.schema import CACHE_KEY_SERIALISED_SCHEMA
from open_targets_platform_mcp.tools.schema.subschema import CACHE_KEY_CATEGORY_SUBSCHEMAS, build_category_subschemas
from open_targets_platform_mcp.tools.schema.type_graph import CACHE_KEY_SCHEMA, CACHE_KEY_TYPE_GRAPH, build_type_graph


async def prepare_cache() -> None:
    """Pre-fetch the GraphQL schema, type graph, and category subschemas."""
    schema = await fetch_graphql_schema()
    cache.set(CACHE_KEY_SCHEMA, schema)
    cache.set(CACHE_KEY_SERIALISED_SCHEMA, print_schema(schema))
    cache.set(CACHE_KEY_TYPE_GRAPH, build_type_graph(schema))
    cache.set(CACHE_KEY_CATEGORY_SUBSCHEMAS, build_category_subschemas(settings.subschema_depth))


async def create_server() -> FastMCP:
    """Set up the MCP server and register all tools.

    This function registers tools based on current configuration.

    Returns:
        FastMCP: Configured MCP server instance with all tools registered
    """
    favicon_bytes = resources.files("open_targets_platform_mcp.static").joinpath("favicon.png").read_bytes()
    data_uri = f"data:image/png;base64,{base64.b64encode(favicon_bytes).decode('utf-8')}"

    await prepare_cache()

    mcp = FastMCP(
        name=settings.server_name,
        icons=[Icon(src=data_uri, mimeType="image/png")],
        mask_error_details=True,
    )

    if settings.rate_limiting_enabled:
        mcp.add_middleware(
            AdaptiveRateLimitingMiddleware(
                global_max_requests_per_second=3,
                global_burst_capacity=100,
                session_max_requests_per_second=3,
                session_burst_capacity=6,
            ),
        )

    mcp.tool(get_open_targets_graphql_schema)
    mcp.tool(get_type_dependencies)
    mcp.tool(
        search_entities,
        description=resources.files("open_targets_platform_mcp.tools.search_entities")
        .joinpath("description.txt")
        .read_text(encoding="utf-8"),
    )

    if settings.jq_enabled:
        query_function = query_with_jq
        query_description = (
            resources.files("open_targets_platform_mcp.tools.query")
            .joinpath("with_jq_description.txt")
            .read_text(encoding="utf-8")
        )
        batch_query_function = batch_query_with_jq
        batch_query_description = (
            resources.files("open_targets_platform_mcp.tools.batch_query")
            .joinpath("with_jq_description.txt")
            .read_text(encoding="utf-8")
        )
    else:
        query_function = query_without_jq
        query_description = (
            resources.files("open_targets_platform_mcp.tools.query")
            .joinpath("without_jq_description.txt")
            .read_text(encoding="utf-8")
        )
        batch_query_function = batch_query_without_jq
        batch_query_description = (
            resources.files("open_targets_platform_mcp.tools.batch_query")
            .joinpath("without_jq_description.txt")
            .read_text(encoding="utf-8")
        )

    mcp.tool(query_function, name="query_open_targets_graphql", description=query_description)
    mcp.tool(batch_query_function, name="batch_query_open_targets_graphql", description=batch_query_description)

    return mcp
