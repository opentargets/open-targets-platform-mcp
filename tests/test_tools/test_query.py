"""Tests for query tool."""

import pytest

from otar_mcp.tools.query import query_open_targets_graphql


def test_query_open_targets_graphql_returns_dict(sample_query_string: str) -> None:
    """Test that query_open_targets_graphql returns a dictionary."""
    result = query_open_targets_graphql(sample_query_string)
    assert isinstance(result, dict)
