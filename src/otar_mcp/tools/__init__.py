"""MCP tools for OpenTargets API."""

# Import all tools to make them available when this package is imported
from otar_mcp.tools import batch_query, query, schema, search_entity

__all__ = ["batch_query", "query", "schema", "search_entity"]
