"""General utilities for GraphQL schema operations.

This module provides generic helper functions such as loading category
definitions from assets and converting schema types to SDL strings.
"""

import json
from importlib import resources

from graphql import GraphQLSchema, print_type


def load_categories() -> dict[str, dict[str, str | list[str]]]:
    """Load categories from the assets JSON file.

    Returns:
        Dict mapping category names to their metadata (description, types).
    """
    categories_bytes = resources.files("open_targets_platform_mcp.assets").joinpath("categories.json").read_bytes()
    result: dict[str, dict[str, str | list[str]]] = json.loads(categories_bytes)
    return result


def types_to_sdl(type_names: set[str], schema: GraphQLSchema, *, strip_descriptions: bool = False) -> str:
    """Convert a set of type names to SDL string.

    Args:
        type_names: Set of type names to convert
        schema: The GraphQL schema object
        strip_descriptions: If True, strips type-level descriptions but
            preserves field/argument descriptions.
    """
    sdl_parts: list[str] = []
    for type_name in sorted(type_names):
        graphql_type = schema.type_map.get(type_name)
        if not graphql_type:
            continue

        original_type_desc = None
        if strip_descriptions and hasattr(graphql_type, "description"):
            original_type_desc = getattr(graphql_type, "description", None)
            graphql_type.description = None  # type: ignore[union-attr]

        sdl_parts.append(print_type(graphql_type))

        if strip_descriptions and hasattr(graphql_type, "description"):
            graphql_type.description = original_type_desc  # type: ignore[union-attr]

    return "\n\n".join(sdl_parts)
