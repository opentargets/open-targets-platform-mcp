"""Schema tools for OpenTargets MCP."""

from open_targets_platform_mcp.tools.schema.schema import (
    get_open_targets_graphql_schema,
    prefetch_schema,
)
from open_targets_platform_mcp.tools.schema.subschema import (
    CategorySubschema,
    CategorySubschemas,
    get_categories_for_docstring,
    get_category_subschemas,
    prefetch_category_subschemas,
)
from open_targets_platform_mcp.tools.schema.type_graph import (
    TypeGraph,
    get_cached_schema,
    get_reachable_types_with_depth,
    get_type_dependencies,
    get_type_graph,
    prefetch_type_graph,
)

__all__ = [
    "CategorySubschema",
    "CategorySubschemas",
    "TypeGraph",
    "get_cached_schema",
    "get_categories_for_docstring",
    "get_category_subschemas",
    "get_open_targets_graphql_schema",
    "get_reachable_types_with_depth",
    "get_type_dependencies",
    "get_type_graph",
    "prefetch_category_subschemas",
    "prefetch_schema",
    "prefetch_type_graph",
]
