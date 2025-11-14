"""Tests for schema tool."""

import pytest

from otar_mcp.tools.schema import get_open_targets_graphql_schema


def test_get_open_targets_graphql_schema_returns_dict() -> None:
    """Test that get_open_targets_graphql_schema returns a dictionary."""
    result = get_open_targets_graphql_schema()
    assert isinstance(result, dict)
    # Result should have either 'schema' or 'error' key
    assert "schema" in result or "error" in result
