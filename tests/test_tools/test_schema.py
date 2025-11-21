"""Tests for schema tool."""

from otar_mcp.tools.schema import get_open_targets_graphql_schema

# Access the underlying function (the decorated function is a FunctionTool)
get_schema_fn = (
    get_open_targets_graphql_schema.fn
    if hasattr(get_open_targets_graphql_schema, "fn")
    else get_open_targets_graphql_schema
)


def test_get_open_targets_graphql_schema_returns_dict() -> None:
    """Test that get_open_targets_graphql_schema returns a dictionary."""
    result = get_schema_fn()
    assert isinstance(result, dict)
    # Result should have either 'schema' or 'error' key
    assert "schema" in result or "error" in result
