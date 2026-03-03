"""Category-based subschemas for the OpenTargets GraphQL schema."""

import json
from dataclasses import dataclass, field
from importlib import resources
from typing import Literal

from graphql import GraphQLSchema, print_type

from open_targets_platform_mcp.cache import AsyncCache
from open_targets_platform_mcp.settings import settings
from open_targets_platform_mcp.tools.schema.type_graph import (
    TypeGraph,
    get_reachable_types_with_depth,
    schema_cache,
    type_graph_cache,
)

# Error messages
_ERR_SUBSCHEMAS_NOT_INIT = "Category subschemas not initialized. Call prefetch_category_subschemas() at server startup."

category_subschemas_cache = AsyncCache["CategorySubschemas"]()


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


def _load_categories() -> dict[str, dict[str, str | list[str]]]:
    """Load categories from the assets JSON file.

    Returns:
        Dict mapping category names to their metadata (description, types).
    """
    categories_bytes = resources.files("open_targets_platform_mcp.assets").joinpath("categories.json").read_bytes()
    result: dict[str, dict[str, str | list[str]]] = json.loads(categories_bytes)
    return result


def types_to_sdl(type_names: set[str], schema: GraphQLSchema) -> str:
    """Convert a set of type names to SDL string.

    Strips type-level descriptions, preserves field/argument descriptions.
    """
    sdl_parts: list[str] = []
    for type_name in sorted(type_names):
        graphql_type = schema.type_map.get(type_name)
        if not graphql_type:
            continue

        # Store and clear type-level description only
        original_type_desc = getattr(graphql_type, "description", None)
        if hasattr(graphql_type, "description"):
            graphql_type.description = None  # type: ignore[union-attr]

        sdl_parts.append(print_type(graphql_type))

        # Restore type description
        if hasattr(graphql_type, "description"):
            graphql_type.description = original_type_desc  # type: ignore[union-attr]

    return "\n\n".join(sdl_parts)


def _build_category_subschema(
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
    sdl = types_to_sdl(expanded_types, schema)

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


async def build_category_subschemas() -> CategorySubschemas:
    """Build subschemas for all categories.

    Args:
        depth: Expansion depth (int or "exhaustive")

    Returns:
        CategorySubschemas containing all category subschemas
    """
    graph = await type_graph_cache.get()
    schema = await schema_cache.get()
    categories = _load_categories()

    subschemas: dict[str, CategorySubschema] = {}

    depth = settings.subschema_depth

    for category_name, category_data in categories.items():
        subschemas[category_name] = _build_category_subschema(
            category_name,
            category_data,
            graph,
            schema,
            depth,
        )

    return CategorySubschemas(subschemas=subschemas, depth=depth)


def get_categories_for_docstring() -> str:
    """Format categories for inclusion in tool docstring.

    Returns:
        Formatted string listing all categories with descriptions.
    """
    categories = _load_categories()

    lines = ["Available categories:"]
    for name, data in sorted(categories.items()):
        description = data.get("description", "")
        if isinstance(description, str):
            lines.append(f"  - {name}: {description}")
        else:
            lines.append(f"  - {name}")

    return "\n".join(lines)


category_subschemas_cache.set_factory(build_category_subschemas)
