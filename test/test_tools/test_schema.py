"""Tests for schema tool."""

from unittest.mock import AsyncMock, patch

import pytest
from graphql import GraphQLSchema, build_schema

from open_targets_platform_mcp.tools.schema import schema
from open_targets_platform_mcp.tools.schema.caches import (
    category_subschemas_cache,
    schema_cache,
    type_graph_cache,
)


@pytest.fixture
def clear_cache():
    """Clear the schema cache before and after each test."""
    schema_cache.clear()
    type_graph_cache.clear()
    category_subschemas_cache.clear()
    yield
    schema_cache.clear()
    type_graph_cache.clear()
    category_subschemas_cache.clear()


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
async def test_schema_cache_populates_properly(clear_cache, mock_graphql_schema) -> None:
    """Test that schema_cache fetches and caches the schema."""
    mock_factory = AsyncMock(return_value=mock_graphql_schema)
    schema_cache.set_factory(mock_factory)

    result = await schema_cache.get()

    assert result is mock_graphql_schema
    mock_factory.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_open_targets_graphql_schema_returns_filtered_schema(
    clear_cache,
    mock_graphql_schema,
) -> None:
    """Test that get_open_targets_graphql_schema returns filtered schema by category."""
    with patch(
        "open_targets_platform_mcp.tools.schema.caches.fetch_graphql_schema",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = mock_graphql_schema

        # Now get the schema with a category
        result = await schema.get_open_targets_graphql_schema(["clinical-genetics"])

    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_get_open_targets_graphql_schema_raises_for_invalid_category(
    clear_cache,
    mock_graphql_schema,
) -> None:
    """Test that get_open_targets_graphql_schema raises error for invalid category."""
    with patch(
        "open_targets_platform_mcp.tools.schema.caches.fetch_graphql_schema",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = mock_graphql_schema

        with pytest.raises(ValueError, match="Invalid category"):
            await schema.get_open_targets_graphql_schema(["nonexistent-category"])


@pytest.mark.asyncio
async def test_multiple_categories_combines_types(clear_cache, mock_graphql_schema) -> None:
    """Test that multiple categories combine their types."""
    with patch(
        "open_targets_platform_mcp.tools.schema.caches.fetch_graphql_schema",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = mock_graphql_schema

        result = await schema.get_open_targets_graphql_schema(
            ["clinical-genetics", "drug-mechanisms"],
        )

        assert isinstance(result, str)
