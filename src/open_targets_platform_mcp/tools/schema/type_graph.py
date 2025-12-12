"""Type relationship graph for the OpenTargets GraphQL schema."""

from dataclasses import dataclass, field
from typing import Annotated

from graphql import (
    GraphQLSchema,
    get_named_type,
    is_enum_type,
    is_input_object_type,
    is_interface_type,
    is_object_type,
    is_union_type,
    print_type,
)
from pydantic import Field

from open_targets_platform_mcp.client.graphql import fetch_graphql_schema

# Built-in scalar types to filter out
_BUILTIN_SCALARS = {"String", "Int", "Float", "Boolean", "ID"}

# Module-level cache for the schema object (needed for SDL extraction)
_cached_schema: GraphQLSchema | None = None

# Module-level cache for type graph (pre-fetched at startup)
_cached_type_graph: "TypeGraph | None" = None

# Error messages
_ERR_TYPE_GRAPH_NOT_INIT = (
    "Type graph not initialized. Call prefetch_type_graph() at server startup."
)
_ERR_SCHEMA_NOT_INIT = (
    "Schema not initialized. Call prefetch_type_graph() at server startup."
)


@dataclass
class TypeGraph:
    """Complete type relationship graph from the GraphQL schema."""

    # Adjacency dict: type_name -> {referenced_type_name: [field_names]}
    adjacency: dict[str, dict[str, list[str]]] = field(default_factory=dict)

    # Type metadata: type_name -> category (object/interface/union/enum)
    types: dict[str, str] = field(default_factory=dict)

    # Reverse adjacency: type_name -> set of types that reference it
    reverse_adjacency: dict[str, set[str]] = field(default_factory=dict)


def _is_custom_type(type_name: str) -> bool:
    """Check if a type name represents a custom (non-built-in) type.

    Filters out:
    - Introspection types (starting with __)
    - Built-in scalars (String, Int, Float, Boolean, ID)
    """
    return not type_name.startswith("__") and type_name not in _BUILTIN_SCALARS


def _get_type_category(graphql_type: object) -> str:
    """Determine the category of a GraphQL type."""
    if is_object_type(graphql_type):
        return "object"
    if is_interface_type(graphql_type):
        return "interface"
    if is_union_type(graphql_type):
        return "union"
    if is_enum_type(graphql_type):
        return "enum"
    if is_input_object_type(graphql_type):
        return "input_object"
    return "scalar"


def _add_field_reference(
    adjacency: dict[str, dict[str, list[str]]],
    source_type: str,
    target_type: str,
    field_name: str,
) -> None:
    """Add a field reference to the adjacency dict."""
    if target_type not in adjacency[source_type]:
        adjacency[source_type][target_type] = []
    adjacency[source_type][target_type].append(field_name)


def _extract_field_dependencies(
    graphql_type: object,
    adjacency: dict[str, dict[str, list[str]]],
    type_name: str,
) -> None:
    """Extract type dependencies from object/interface/input fields."""
    for field_name, field_obj in graphql_type.fields.items():  # type: ignore[union-attr]
        base_type = get_named_type(field_obj.type)
        if base_type and _is_custom_type(base_type.name):
            _add_field_reference(adjacency, type_name, base_type.name, field_name)


def _extract_union_dependencies(
    graphql_type: object,
    adjacency: dict[str, dict[str, list[str]]],
    type_name: str,
) -> None:
    """Extract type dependencies from union member types."""
    for member in graphql_type.types:  # type: ignore[union-attr]
        if _is_custom_type(member.name):
            _add_field_reference(adjacency, type_name, member.name, "<union>")


def _build_reverse_adjacency(
    adjacency: dict[str, dict[str, list[str]]],
) -> dict[str, set[str]]:
    """Build reverse adjacency from the forward adjacency dict."""
    reverse: dict[str, set[str]] = {}
    for source_type, targets in adjacency.items():
        for target_type in targets:
            if target_type not in reverse:
                reverse[target_type] = set()
            reverse[target_type].add(source_type)
    return reverse


def build_type_graph(schema: GraphQLSchema) -> TypeGraph:
    """Build the type relationship graph from a GraphQL schema.

    This function examines all types in the schema and builds an adjacency
    dict mapping each custom type to the custom types it references.

    Args:
        schema: The GraphQL schema object from graphql-core

    Returns:
        TypeGraph: The complete type relationship graph
    """
    graph = TypeGraph()

    for type_name, graphql_type in schema.type_map.items():
        if not _is_custom_type(type_name):
            continue

        graph.types[type_name] = _get_type_category(graphql_type)
        graph.adjacency[type_name] = {}

        # Extract dependencies based on type category
        has_fields = (
            is_object_type(graphql_type)
            or is_interface_type(graphql_type)
            or is_input_object_type(graphql_type)
        )
        if has_fields:
            _extract_field_dependencies(graphql_type, graph.adjacency, type_name)
        elif is_union_type(graphql_type):
            _extract_union_dependencies(graphql_type, graph.adjacency, type_name)

    graph.reverse_adjacency = _build_reverse_adjacency(graph.adjacency)
    return graph


async def prefetch_type_graph() -> None:
    """Pre-fetch and cache the type graph at server startup.

    This function should be called once during server initialization
    to build the type relationship graph from the schema.
    """
    global _cached_type_graph, _cached_schema  # noqa: PLW0603
    schema_obj = await fetch_graphql_schema()
    _cached_schema = schema_obj
    _cached_type_graph = build_type_graph(schema_obj)


def get_type_graph() -> TypeGraph:
    """Get the cached type graph.

    Returns:
        TypeGraph: The pre-fetched type relationship graph.

    Raises:
        RuntimeError: If type graph was not pre-fetched at startup.
    """
    if _cached_type_graph is None:
        raise RuntimeError(_ERR_TYPE_GRAPH_NOT_INIT)
    return _cached_type_graph


def get_cached_schema() -> GraphQLSchema:
    """Get the cached GraphQL schema object.

    Returns:
        The pre-fetched GraphQL schema.

    Raises:
        RuntimeError: If schema was not pre-fetched at startup.
    """
    if _cached_schema is None:
        raise RuntimeError(_ERR_SCHEMA_NOT_INIT)
    return _cached_schema


def _get_reachable_types(graph: TypeGraph, start_type: str) -> set[str]:
    """BFS traversal to find all reachable types exhaustively.

    Args:
        graph: The type graph to traverse
        start_type: The type name to start from

    Returns:
        Set of all reachable type names (including start_type)
    """
    visited: set[str] = {start_type}
    current_level: set[str] = {start_type}

    while current_level:
        next_level: set[str] = set()

        for type_name in current_level:
            for referenced_type in graph.adjacency.get(type_name, {}):
                if referenced_type not in visited:
                    visited.add(referenced_type)
                    next_level.add(referenced_type)

        current_level = next_level

    return visited


def get_reachable_types_with_depth(
    graph: TypeGraph,
    start_types: set[str],
    max_depth: int | None = None,
) -> set[str]:
    """BFS traversal with optional depth limit.

    Args:
        graph: The type graph to traverse
        start_types: Set of type names to start from
        max_depth: Maximum depth to traverse (None = exhaustive)

    Returns:
        Set of all reachable type names within depth limit
        (including start types)
    """
    visited: set[str] = set(start_types)
    current_level: set[str] = set(start_types)
    current_depth = 0

    while current_level:
        if max_depth is not None and current_depth >= max_depth:
            break

        next_level: set[str] = set()

        for type_name in current_level:
            for referenced_type in graph.adjacency.get(type_name, {}):
                if referenced_type not in visited:
                    visited.add(referenced_type)
                    next_level.add(referenced_type)

        current_level = next_level
        current_depth += 1

    return visited


def _build_type_not_found_message(type_name: str, available_types: list[str]) -> str:
    """Build a helpful error message for type not found errors."""
    similar = [t for t in available_types if type_name.lower() in t.lower()][:5]
    if similar:
        suggestion = f" Similar types: {', '.join(similar)}"
    else:
        suggestion = f" Available types include: {', '.join(available_types[:10])}"
    return f"Type '{type_name}' not found in schema.{suggestion}"


def _types_to_sdl(type_names: set[str], schema: GraphQLSchema) -> str:
    """Convert a set of type names to SDL string."""
    sdl_parts: list[str] = []
    for type_name in sorted(type_names):
        graphql_type = schema.type_map.get(type_name)
        if graphql_type:
            sdl_parts.append(print_type(graphql_type))
    return "\n\n".join(sdl_parts)


async def get_type_dependencies(
    type_names: Annotated[
        list[str],
        Field(
            description="List of GraphQL type names to explore "
            "(e.g., ['Target', 'Disease', 'Drug'])",
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
    graph = get_type_graph()
    available_types = sorted(graph.types.keys())

    # Validate all type names first
    invalid_types = [t for t in type_names if t not in graph.types]
    if invalid_types:
        msg = _build_type_not_found_message(invalid_types[0], available_types)
        raise ValueError(msg)

    if _cached_schema is None:
        raise RuntimeError(_ERR_SCHEMA_NOT_INIT)

    # Get reachable types for each input type
    reachable_by_type: dict[str, set[str]] = {}
    for type_name in type_names:
        reachable_by_type[type_name] = _get_reachable_types(graph, type_name)

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
            result[type_name] = _types_to_sdl(specific_types, _cached_schema)
        else:
            result[type_name] = ""

    # Add shared dependencies
    if shared_types:
        result["shared"] = _types_to_sdl(shared_types, _cached_schema)
    else:
        result["shared"] = ""

    return result
