"""Tool for listing all types in the Open Targets Platform GraphQL schema."""

from typing import Annotated, Any

from pydantic import Field

from open_targets_platform_mcp.tools.schema_explorer.schema_explorer import get_schema_explorer


async def list_schema_types(
    type_filter: Annotated[
        list[str] | None,
        Field(
            description=(
                "Filter by type category: 'query', 'object', 'input', 'enum', 'scalar'. "
                "Example: ['query', 'object'] returns only query fields and object types. "
                "Default: returns all categories."
            )
        ),
    ] = None,
) -> dict[str, Any]:
    """List all types in the Open Targets Platform GraphQL schema.

    Provides a high-level overview of the schema structure without details.
    This is the starting point for RLM-based schema exploration.

    Args:
        type_filter: Optional list of type categories to include

    Returns:
        Dictionary with categorized type lists (query_fields, object_types,
        input_types, enum_types, scalar_types)
    """
    explorer = await get_schema_explorer()

    # Default to all categories if no filter
    if type_filter is None:
        type_filter = ["query", "object", "input", "enum", "scalar"]

    # Normalize to lowercase
    type_filter = [f.lower() for f in type_filter]

    result = {}

    if "query" in type_filter:
        result["query_fields"] = explorer.list_query_fields()

    if "object" in type_filter:
        result["object_types"] = explorer.list_object_types()

    if "input" in type_filter:
        result["input_types"] = explorer.list_input_types()

    if "enum" in type_filter:
        result["enum_types"] = explorer.list_enum_types()

    if "scalar" in type_filter:
        result["scalar_types"] = explorer.list_scalar_types()

    return result
