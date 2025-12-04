"""Tool for fetching the OpenTargets GraphQL schema."""

from pathlib import Path

from otar_mcp.mcp_instance import mcp


@mcp.tool()
def get_open_targets_graphql_schema() -> dict:
    """Retrieve the Open Targets GraphQL schema for query construction.

    Returns:
        dict: Schema string in format {'schema': '...'} containing GraphQL type definitions or error message.
    """
    # Dynamic path relative to this file
    # This file is in src/otar_mcp/tools/schema.py
    # We want src/otar_mcp/data/documented_schema.txt
    schema_path = Path(__file__).parent.parent / "data" / "documented_schema.txt"

    try:
        schema = schema_path.read_text(encoding="utf-8")
    except Exception as e:
        return {"error": f"Failed to load Open Targets GraphQL schema: {e!s}"}
    else:
        return {"schema": schema}
