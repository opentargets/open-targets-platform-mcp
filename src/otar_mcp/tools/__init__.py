"""MCP tools for OpenTargets API."""

# Import all tools to make them available when this package is imported
from otar_mcp.tools import batch_query, examples, query, schema, search, search_entity, semantic_search

__all__ = ["batch_query", "examples", "query", "schema", "search", "search_entity", "semantic_search"]
