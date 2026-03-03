"""GraphQL schema type graph and traversal utilities.

This module provides the `TypeGraph` dataclass and functions to build and
traverse a graph representing the dependencies between GraphQL types.
"""

from dataclasses import dataclass, field

from graphql import (
    GraphQLSchema,
    get_named_type,
    is_enum_type,
    is_input_object_type,
    is_interface_type,
    is_object_type,
    is_union_type,
)

# Built-in scalar types to filter out
_BUILTIN_SCALARS = {"String", "Int", "Float", "Boolean", "ID"}


@dataclass
class TypeGraph:
    """Complete type relationship graph from the GraphQL schema."""

    # Adjacency dict: type_name -> {referenced_type_name: [field_names]}
    adjacency: dict[str, dict[str, list[str]]] = field(default_factory=dict[str, dict[str, list[str]]])

    # Type metadata: type_name -> category (object/interface/union/enum)
    types: dict[str, str] = field(default_factory=dict[str, str])

    # Reverse adjacency: type_name -> set of types that reference it
    reverse_adjacency: dict[str, set[str]] = field(default_factory=dict[str, set[str]])


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
            is_object_type(graphql_type) or is_interface_type(graphql_type) or is_input_object_type(graphql_type)
        )
        if has_fields:
            _extract_field_dependencies(graphql_type, graph.adjacency, type_name)
        elif is_union_type(graphql_type):
            _extract_union_dependencies(graphql_type, graph.adjacency, type_name)

    graph.reverse_adjacency = _build_reverse_adjacency(graph.adjacency)
    return graph


def get_reachable_types(graph: TypeGraph, start_type: str) -> set[str]:
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
