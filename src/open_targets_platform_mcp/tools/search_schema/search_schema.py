"""Tool for searching the GraphQL schema for types and fields."""

from typing import Annotated, Any

from pydantic import Field

from open_targets_platform_mcp.tools.schema_explorer.schema_explorer import get_schema_explorer


async def search_schema(
    pattern: Annotated[
        str,
        Field(
            description=(
                "Search pattern (case-insensitive substring match). "
                "Examples: 'cancer', 'clinical trial', 'association score'"
            )
        ),
    ],
    search_in: Annotated[
        list[str] | None,
        Field(
            description=(
                "Where to search: 'field_names', 'type_names', 'descriptions'. "
                "Default: searches all locations. "
                "Example: ['field_names', 'descriptions'] searches fields and descriptions but not type names."
            )
        ),
    ] = None,
) -> dict[str, Any]:
    """Search the GraphQL schema for types and fields matching a pattern.

    Use this to discover relevant parts of the schema based on concepts or keywords.

    Args:
        pattern: Search pattern (case-insensitive)
        search_in: Optional list of locations to search in

    Returns:
        Dictionary with matching types and fields
    """
    explorer = await get_schema_explorer()

    # Default to search everywhere
    if search_in is None:
        search_in = ["field_names", "type_names", "descriptions"]

    # Normalize
    search_in = [s.lower() for s in search_in]

    matches: dict[str, list[dict]] = {"types": [], "fields": []}

    # Search type names
    if "type_names" in search_in:
        matches["types"].extend(explorer.search_types(pattern))

    # Search field names
    if "field_names" in search_in:
        matches["fields"].extend(explorer.search_fields(pattern))

    # Search descriptions
    if "descriptions" in search_in:
        # Get matches from descriptions
        desc_matches = explorer.search_descriptions(pattern)

        # Merge with existing matches (avoiding duplicates)
        for match in desc_matches:
            if "type_name" in match:  # Field match
                # Check if already in fields
                if not any(
                    f["type_name"] == match["type_name"] and f["field_name"] == match["field_name"]
                    for f in matches["fields"]
                ):
                    matches["fields"].append(match)
            else:  # Type match
                if not any(t["name"] == match["name"] for t in matches["types"]):
                    matches["types"].append(match)

    return {
        "query": pattern,
        "matches": matches,
        "total_matches": len(matches["types"]) + len(matches["fields"]),
    }
