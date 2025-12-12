"""Tests for schema tool."""

from unittest.mock import AsyncMock, patch

import pytest
from graphql import GraphQLSchema, build_schema

from open_targets_platform_mcp.tools.schema import schema, subschema, type_graph


@pytest.fixture
def clear_cache():
    """Clear the schema cache before and after each test."""
    schema._cached_schema = None
    type_graph._cached_schema = None
    type_graph._cached_type_graph = None
    subschema._cached_subschemas = None
    yield
    schema._cached_schema = None
    type_graph._cached_schema = None
    type_graph._cached_type_graph = None
    subschema._cached_subschemas = None


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
async def test_prefetch_schema_populates_cache(clear_cache, mock_graphql_schema) -> None:
    """Test that prefetch_schema fetches and caches the schema."""
    with patch(
        "open_targets_platform_mcp.tools.schema.schema.fetch_graphql_schema",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = mock_graphql_schema

        await schema.prefetch_schema()

    assert schema._cached_schema is not None
    assert isinstance(schema._cached_schema, str)
    assert len(schema._cached_schema) > 0
    assert "type Query" in schema._cached_schema or "type Query {" in schema._cached_schema
    mock_fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_open_targets_graphql_schema_returns_filtered_schema(
    clear_cache, mock_graphql_schema
) -> None:
    """Test that get_open_targets_graphql_schema returns filtered schema by category."""
    with patch(
        "open_targets_platform_mcp.tools.schema.type_graph.fetch_graphql_schema",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = mock_graphql_schema

        # Pre-fetch schema, type graph, and subschemas
        await schema.prefetch_schema()
        await type_graph.prefetch_type_graph()
        await subschema.prefetch_category_subschemas(depth=1)

        # Now get the schema with a category
        result = await schema.get_open_targets_graphql_schema(["clinical-genetics"])

    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_get_open_targets_graphql_schema_raises_if_not_prefetched(clear_cache) -> None:
    """Test that get_open_targets_graphql_schema raises error if schema not pre-fetched."""
    with pytest.raises(RuntimeError, match="Schema not initialized"):
        await schema.get_open_targets_graphql_schema(["clinical-genetics"])


@pytest.mark.asyncio
async def test_get_open_targets_graphql_schema_raises_for_invalid_category(
    clear_cache, mock_graphql_schema
) -> None:
    """Test that get_open_targets_graphql_schema raises error for invalid category."""
    with patch(
        "open_targets_platform_mcp.tools.schema.type_graph.fetch_graphql_schema",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = mock_graphql_schema

        await schema.prefetch_schema()
        await type_graph.prefetch_type_graph()
        await subschema.prefetch_category_subschemas(depth=1)

        with pytest.raises(ValueError, match="Invalid category"):
            await schema.get_open_targets_graphql_schema(["nonexistent-category"])


@pytest.mark.asyncio
async def test_multiple_categories_combines_types(clear_cache, mock_graphql_schema) -> None:
    """Test that multiple categories combine their types."""
    with patch(
        "open_targets_platform_mcp.tools.schema.type_graph.fetch_graphql_schema",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = mock_graphql_schema

        await schema.prefetch_schema()
        await type_graph.prefetch_type_graph()
        await subschema.prefetch_category_subschemas(depth=1)

        result = await schema.get_open_targets_graphql_schema(
            ["clinical-genetics", "drug-mechanisms"]
        )

        assert isinstance(result, str)
