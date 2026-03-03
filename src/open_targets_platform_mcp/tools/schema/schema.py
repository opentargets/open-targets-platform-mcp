"""Tool for fetching the Open Targets Platform GraphQL schema."""

from importlib import resources
from typing import Annotated

from pydantic import Field

from open_targets_platform_mcp.tools.schema.caches import category_subschemas_cache, schema_cache
from open_targets_platform_mcp.tools.schema.helper import load_categories, types_to_sdl


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
    sdl = types_to_sdl(all_types, schema_obj, strip_descriptions=True)

    # Append common mistakes guide
    common_mistakes_guide = (
        resources.files("open_targets_platform_mcp.tools.schema")
        .joinpath("common_mistakes_guide.txt")
        .read_text(encoding="utf-8")
    )
    return sdl + "\n" + common_mistakes_guide


def get_categories_for_docstring() -> str:
    """Format categories for inclusion in tool docstring.

    Returns:
        Formatted string listing all categories with descriptions.
    """
    categories = load_categories()

    lines = ["Available categories:"]
    for name, data in sorted(categories.items()):
        description = data.get("description", "")
        if isinstance(description, str):
            lines.append(f"  - {name}: {description}")
        else:
            lines.append(f"  - {name}")

    return "\n".join(lines)


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
