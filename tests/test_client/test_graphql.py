"""Tests for GraphQL client."""

import pytest

from otar_mcp.client.graphql import execute_graphql_query, fetch_graphql_schema


def test_execute_graphql_query_returns_dict(mock_api_endpoint: str, sample_query_string: str) -> None:
    """Test that execute_graphql_query returns a dictionary."""
    result = execute_graphql_query(mock_api_endpoint, sample_query_string)
    assert isinstance(result, dict)
    assert "status" in result
