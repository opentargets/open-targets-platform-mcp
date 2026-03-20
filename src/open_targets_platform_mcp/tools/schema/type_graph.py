"""Type relationship graph for the OpenTargets GraphQL schema."""

from typing import Annotated

from pydantic import Field

from open_targets_platform_mcp.tools.schema.caches import schema_cache, type_graph_cache
from open_targets_platform_mcp.tools.schema.helper import (
    get_reachable_types,
    types_to_sdl,
)


def _build_type_not_found_message(type_name: str, available_types: list[str]) -> str:
    """Build a helpful error message for type not found errors."""
    similar = [t for t in available_types if type_name.lower() in t.lower()][:5]
    if similar:
        suggestion = f" Similar types: {', '.join(similar)}"
    else:
        suggestion = f" Available types include: {', '.join(available_types[:10])}"
    return f"Type '{type_name}' not found in schema.{suggestion}"


async def get_type_dependencies(
    type_names: Annotated[
        list[str],
        Field(
            description="List of GraphQL type names to explore (e.g., ['Target', 'Disease', 'Drug'])",
        ),
    ],
) -> dict[str, str]:
    """Get schema subsets for types, separated by specific and shared deps.

    Given a list of type names, returns SDL (Schema Definition Language)
    organized into type-specific dependencies and shared dependencies.

    Returns a dict with:
        - One key per input type: SDL for types ONLY reachable from that type
        - "shared" key: SDL for types reachable from multiple input types

    Examples:
        - get_type_dependencies(["Target"]) - All deps under "Target" key
        - get_type_dependencies(["Target", "Drug"]) - Separated + shared

    Args:
        type_names: List of GraphQL type names to start exploration from

    Returns:
        dict with type-specific SDL and shared SDL

    Raises:
        ValueError: If any type_name is not found in the schema
    """
    graph = await type_graph_cache.get()
    available_types = sorted(graph.types.keys())

    # Validate all type names first
    invalid_types = [t for t in type_names if t not in graph.types]
    if invalid_types:
        msg = _build_type_not_found_message(invalid_types[0], available_types)
        raise ValueError(msg)

    # Get reachable types for each input type
    reachable_by_type: dict[str, set[str]] = {}
    for type_name in type_names:
        reachable_by_type[type_name] = get_reachable_types(graph, type_name)

    # Find shared types (reachable from 2+ input types)
    all_types: set[str] = set()
    for types in reachable_by_type.values():
        all_types.update(types)

    type_counts: dict[str, int] = {}
    for types in reachable_by_type.values():
        for t in types:
            type_counts[t] = type_counts.get(t, 0) + 1

    shared_types = {t for t, count in type_counts.items() if count > 1}

    # Build result dict
    result: dict[str, str] = {}

    # Add type-specific dependencies (excluding shared)
    for type_name in type_names:
        specific_types = reachable_by_type[type_name] - shared_types
        if specific_types:
            result[type_name] = types_to_sdl(specific_types, await schema_cache.get())
        else:
            result[type_name] = ""

    # Add shared dependencies
    if shared_types:
        result["shared"] = types_to_sdl(shared_types, await schema_cache.get())
    else:
        result["shared"] = ""

    return result
