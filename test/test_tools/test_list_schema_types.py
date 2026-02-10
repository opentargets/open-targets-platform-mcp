"""Tests for list_schema_types tool."""

from unittest.mock import AsyncMock, patch

import pytest

from open_targets_platform_mcp.tools.list_schema_types.list_schema_types import list_schema_types


@pytest.mark.asyncio
async def test_list_all_types(rich_mock_schema):
    """Test listing all types without filter."""
    with patch(
        "open_targets_platform_mcp.tools.list_schema_types.list_schema_types.get_schema_explorer",
        new_callable=AsyncMock,
    ) as mock_get_explorer:
        from open_targets_platform_mcp.tools.schema_explorer.schema_explorer import SchemaExplorer

        mock_get_explorer.return_value = SchemaExplorer(rich_mock_schema)

        result = await list_schema_types()

        assert "query_fields" in result
        assert "object_types" in result
        assert "input_types" in result
        assert "enum_types" in result
        assert "scalar_types" in result

        # Check query fields
        assert len(result["query_fields"]) == 4
        query_names = [q["name"] for q in result["query_fields"]]
        assert "target" in query_names
        assert "disease" in query_names

        # Check object types
        object_names = [t["name"] for t in result["object_types"]]
        assert "Target" in object_names
        assert "Disease" in object_names
        assert "Query" not in object_names  # Should exclude Query


@pytest.mark.asyncio
async def test_list_query_only(rich_mock_schema):
    """Test filtering to only query fields."""
    with patch(
        "open_targets_platform_mcp.tools.list_schema_types.list_schema_types.get_schema_explorer",
        new_callable=AsyncMock,
    ) as mock_get_explorer:
        from open_targets_platform_mcp.tools.schema_explorer.schema_explorer import SchemaExplorer

        mock_get_explorer.return_value = SchemaExplorer(rich_mock_schema)

        result = await list_schema_types(type_filter=["query"])

        assert "query_fields" in result
        assert "object_types" not in result
        assert "input_types" not in result
        assert "enum_types" not in result
        assert "scalar_types" not in result


@pytest.mark.asyncio
async def test_list_object_types_only(rich_mock_schema):
    """Test filtering to only object types."""
    with patch(
        "open_targets_platform_mcp.tools.list_schema_types.list_schema_types.get_schema_explorer",
        new_callable=AsyncMock,
    ) as mock_get_explorer:
        from open_targets_platform_mcp.tools.schema_explorer.schema_explorer import SchemaExplorer

        mock_get_explorer.return_value = SchemaExplorer(rich_mock_schema)

        result = await list_schema_types(type_filter=["object"])

        assert "query_fields" not in result
        assert "object_types" in result
        assert len(result["object_types"]) > 0


@pytest.mark.asyncio
async def test_list_multiple_filters(rich_mock_schema):
    """Test filtering to multiple categories."""
    with patch(
        "open_targets_platform_mcp.tools.list_schema_types.list_schema_types.get_schema_explorer",
        new_callable=AsyncMock,
    ) as mock_get_explorer:
        from open_targets_platform_mcp.tools.schema_explorer.schema_explorer import SchemaExplorer

        mock_get_explorer.return_value = SchemaExplorer(rich_mock_schema)

        result = await list_schema_types(type_filter=["query", "object"])

        assert "query_fields" in result
        assert "object_types" in result
        assert "input_types" not in result
        assert "enum_types" not in result
        assert "scalar_types" not in result


@pytest.mark.asyncio
async def test_empty_filter(rich_mock_schema):
    """Test with empty filter list."""
    with patch(
        "open_targets_platform_mcp.tools.list_schema_types.list_schema_types.get_schema_explorer",
        new_callable=AsyncMock,
    ) as mock_get_explorer:
        from open_targets_platform_mcp.tools.schema_explorer.schema_explorer import SchemaExplorer

        mock_get_explorer.return_value = SchemaExplorer(rich_mock_schema)

        result = await list_schema_types(type_filter=[])

        # Empty filter should return empty dict
        assert len(result) == 0


@pytest.mark.asyncio
async def test_case_insensitive_filter(rich_mock_schema):
    """Test that filter is case insensitive."""
    with patch(
        "open_targets_platform_mcp.tools.list_schema_types.list_schema_types.get_schema_explorer",
        new_callable=AsyncMock,
    ) as mock_get_explorer:
        from open_targets_platform_mcp.tools.schema_explorer.schema_explorer import SchemaExplorer

        mock_get_explorer.return_value = SchemaExplorer(rich_mock_schema)

        result = await list_schema_types(type_filter=["QUERY", "Object"])

        assert "query_fields" in result
        assert "object_types" in result
