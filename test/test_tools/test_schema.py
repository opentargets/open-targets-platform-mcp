"""Tests for schema tool."""

from unittest.mock import AsyncMock, patch

import pytest
from graphql import GraphQLSchema, build_schema

from open_targets_platform_mcp.tools.schema import schema

# Access the underlying function
get_schema_fn = schema.get_open_targets_graphql_schema


@pytest.fixture
def clear_cache():
    """Clear the schema cache before and after each test."""
    schema._cache.clear()
    yield
    schema._cache.clear()


@pytest.fixture
def mock_graphql_schema() -> GraphQLSchema:
    """Create a mock GraphQL schema for testing."""
    return build_schema(
        """
        type Query {
            target(ensemblId: String!): Target
        }
        type Target {
            id: String!
            approvedSymbol: String
        }
        """,
    )


@pytest.mark.asyncio
async def test_get_open_targets_graphql_schema_returns_string(clear_cache, mock_graphql_schema) -> None:
    """Test that get_open_targets_graphql_schema returns a string."""
    with patch(
        "open_targets_platform_mcp.tools.schema.schema.fetch_graphql_schema",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = mock_graphql_schema

        result = await get_schema_fn()

    assert isinstance(result, str)
    # Result should be non-empty
    assert len(result) > 0
    # Should contain expected schema elements
    assert "type Query" in result or "type Query {" in result
    assert "target" in result.lower()
    mock_fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_open_targets_graphql_schema_caching(clear_cache, mock_graphql_schema) -> None:
    """Test that schema is cached and not fetched multiple times."""
    with patch(
        "open_targets_platform_mcp.tools.schema.schema.fetch_graphql_schema",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = mock_graphql_schema

        # First call - should fetch from API
        result1 = await get_schema_fn()
        assert isinstance(result1, str)
        assert len(result1) > 0

        # Second call - should use cache
        result2 = await get_schema_fn()
        assert isinstance(result2, str)
        assert result1 == result2

        # Should only be called once due to caching
        assert mock_fetch.await_count == 1
