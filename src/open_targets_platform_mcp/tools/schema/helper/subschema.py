"""Category-based GraphQL subschema definitions and builders.

This module provides the `CategorySubschema` models and logic to build
filtered subschemas based on metadata defined in `categories.json`.
"""

from dataclasses import dataclass, field
from typing import Literal

from graphql import GraphQLSchema

from open_targets_platform_mcp.tools.schema.helper.graph import TypeGraph, get_reachable_types_with_depth
from open_targets_platform_mcp.tools.schema.helper.utils import types_to_sdl


@dataclass
class CategorySubschema:
    """Subschema for a single category."""

    name: str
    description: str
    types: set[str]  # All types in the expanded subschema
    sdl: str  # SDL representation of the subschema


@dataclass
class CategorySubschemas:
    """Collection of all category subschemas."""

    # category_name -> CategorySubschema
    subschemas: dict[str, CategorySubschema] = field(default_factory=dict[str, CategorySubschema])

    # Depth used for expansion (for reference)
    depth: int | Literal["exhaustive"] = 1


def build_category_subschema(
    category_name: str,
    category_data: dict[str, str | list[str]],
    graph: TypeGraph,
    schema: GraphQLSchema,
    depth: int | Literal["exhaustive"],
) -> CategorySubschema:
    """Build a subschema for a single category.

    Args:
        category_name: Name of the category
        category_data: Category metadata from categories.json
        graph: The type graph
        schema: The GraphQL schema object
        depth: Expansion depth (int or "exhaustive")

    Returns:
        CategorySubschema for this category
    """
    # Get seed types from category
    types_list = category_data["types"]
    seed_types: set[str] = set(types_list) if isinstance(types_list, list) else set()

    # Filter to types that exist in schema
    valid_seed_types = {t for t in seed_types if t in graph.types}

    # Determine max_depth
    max_depth = None if depth == "exhaustive" else depth

    # Expand types
    expanded_types = get_reachable_types_with_depth(graph, valid_seed_types, max_depth)

    # Convert to SDL
    sdl = types_to_sdl(expanded_types, schema, strip_descriptions=True)

    # Get description (guaranteed to be a string)
    description = category_data.get("description", "")
    if not isinstance(description, str):
        description = ""

    return CategorySubschema(
        name=category_name,
        description=description,
        types=expanded_types,
        sdl=sdl,
    )
