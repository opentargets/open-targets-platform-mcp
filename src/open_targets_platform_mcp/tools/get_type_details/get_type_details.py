"""Tool for getting detailed information about a specific GraphQL type."""

from typing import Annotated, Any

from pydantic import Field

from open_targets_platform_mcp.tools.schema_explorer.schema_explorer import get_schema_explorer


async def get_type_details(
    type_name: Annotated[
        str,
        Field(
            description=(
                "Name of the GraphQL type to inspect. "
                "Examples: 'Target', 'Disease', 'Drug', 'Query'. "
                "Use list_schema_types() first to see available types."
            )
        ),
    ],
) -> dict[str, Any]:
    """Get detailed information about a specific GraphQL type.

    Returns all fields, arguments, descriptions, and relationships for the type.

    Args:
        type_name: The name of the type to inspect

    Returns:
        Dictionary with comprehensive type information

    Raises:
        ValueError: If type doesn't exist in schema
    """
    explorer = await get_schema_explorer()

    try:
        return explorer.get_type_info(type_name)
    except ValueError as e:
        # Enhance error with suggestions
        all_types = (
            [t["name"] for t in explorer.list_object_types()]
            + [t["name"] for t in explorer.list_input_types()]
            + [t["name"] for t in explorer.list_enum_types()]
        )

        # Find similar type names (simple substring matching)
        similar = [t for t in all_types if type_name.lower() in t.lower()][:5]

        error_msg = f"Type '{type_name}' not found in schema."
        if similar:
            error_msg += f" Did you mean one of: {', '.join(similar)}?"
        else:
            error_msg += " Use list_schema_types() to see all available types."

        raise ValueError(error_msg) from e
