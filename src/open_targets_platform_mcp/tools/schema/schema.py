"""Tool for fetching the Open Targets Platform GraphQL schema."""

from importlib import resources
from typing import Annotated

from graphql import print_schema
from pydantic import Field

from open_targets_platform_mcp.cache import AsyncCache
from open_targets_platform_mcp.client.graphql import fetch_graphql_schema
from open_targets_platform_mcp.tools.schema.subschema import (
    category_subschemas_cache,
    get_categories_for_docstring,
    schema_cache,
    types_to_sdl,
)


async def _serialised_schema_cache_factory() -> str:
    schema = await fetch_graphql_schema()
    return print_schema(schema)


serialised_schema_cache = AsyncCache[str](_serialised_schema_cache_factory)


async def get_open_targets_graphql_schema(
    categories: Annotated[
        list[str],
        Field(
            description="List of category names to filter the schema. "
            "Returns only types relevant to the specified categories.",
        ),
    ],
) -> str:
    """Retrieve the Open Targets Platform GraphQL schema by category."""
    # Get subschemas for requested categories
    subschemas = await category_subschemas_cache.get()
    available_categories = sorted(subschemas.subschemas.keys())

    # Validate category names
    invalid_categories = [c for c in categories if c not in subschemas.subschemas]
    if invalid_categories:
        msg = (
            f"Invalid category name(s): {', '.join(invalid_categories)}. "
            f"Available categories: {', '.join(available_categories)}"
        )
        raise ValueError(msg)

    # Collect all types from requested categories
    all_types: set[str] = set()
    for category_name in categories:
        all_types.update(subschemas.subschemas[category_name].types)

    # Generate combined SDL
    schema_obj = await schema_cache.get()
    sdl = types_to_sdl(all_types, schema_obj)

    # Append common mistakes guide
    common_mistakes_guide = (
        resources.files("open_targets_platform_mcp.tools.schema")
        .joinpath("common_mistakes_guide.txt")
        .read_text(encoding="utf-8")
    )
    return sdl + "\n" + common_mistakes_guide


# Dynamically set the docstring with the categories list
get_open_targets_graphql_schema.__doc__ = f"""\
Retrieve the Open Targets Platform GraphQL schema filtered by category.

You MUST specify one or more categories to retrieve the relevant schema subset.
Categories group related GraphQL types into coherent subschemas
(e.g., 'drug-mechanisms', 'genetic-associations', 'target-safety').

The returned schema includes types from the specified categories plus
their dependencies expanded..

Args:
    categories: List of category names to filter the schema. At least
        one category must be specified.

Returns:
    str: the schema text in SDL (Schema Definition Language) format.

Raises:
    RuntimeError: If schema was not pre-fetched at startup.
    ValueError: If an invalid category name is provided.

Examples:
    - get_open_targets_graphql_schema(["drug-mechanisms"]) -> drug types
    - get_open_targets_graphql_schema(["target-safety", "drug-safety"])
        -> combined safety-related types

{get_categories_for_docstring()}
"""
