"""Schema tools for OpenTargets MCP."""

from open_targets_platform_mcp.tools.schema.helper import (
    CategorySubschema,
    CategorySubschemas,
    load_categories,
    types_to_sdl,
)
from open_targets_platform_mcp.tools.schema.schema import (
    get_categories_for_docstring,
    get_open_targets_graphql_schema,
)
from open_targets_platform_mcp.tools.schema.type_graph import (
    TypeGraph,
    get_reachable_types_with_depth,
    get_type_dependencies,
)

__all__ = [
    "CategorySubschema",
    "CategorySubschemas",
    "TypeGraph",
    "get_categories_for_docstring",
    "get_open_targets_graphql_schema",
    "get_reachable_types_with_depth",
    "get_type_dependencies",
    "load_categories",
    "types_to_sdl",
]
