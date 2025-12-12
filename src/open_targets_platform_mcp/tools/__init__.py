"""MCP tools for Open Targets Platform API."""

# Import all tools to make them available when this package is imported
from open_targets_platform_mcp.tools.batch_query.batch_query import batch_query_with_jq, batch_query_without_jq
from open_targets_platform_mcp.tools.query.query import query_with_jq, query_without_jq
from open_targets_platform_mcp.tools.schema.schema import get_open_targets_graphql_schema, prefetch_schema
from open_targets_platform_mcp.tools.schema.type_graph import get_type_dependencies, prefetch_type_graph
from open_targets_platform_mcp.tools.search_entities.search_entities import search_entities

__all__ = [
    "batch_query_with_jq",
    "batch_query_without_jq",
    "get_open_targets_graphql_schema",
    "get_type_dependencies",
    "prefetch_schema",
    "prefetch_type_graph",
    "query_with_jq",
    "query_without_jq",
    "search_entities",
]
