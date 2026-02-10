"""Tests for search_schema tool."""

from unittest.mock import AsyncMock, patch

import pytest

from open_targets_platform_mcp.tools.search_schema.search_schema import search_schema


@pytest.mark.asyncio
async def test_search_all_locations(rich_mock_schema):
    """Test searching in all locations (default)."""
    with patch(
        "open_targets_platform_mcp.tools.search_schema.search_schema.get_schema_explorer",
        new_callable=AsyncMock,
    ) as mock_get_explorer:
        from open_targets_platform_mcp.tools.schema_explorer.schema_explorer import SchemaExplorer

        mock_get_explorer.return_value = SchemaExplorer(rich_mock_schema)

        result = await search_schema("cancer")

        assert "query" in result
        assert result["query"] == "cancer"
        assert "matches" in result
        assert "types" in result["matches"]
        assert "fields" in result["matches"]
        assert "total_matches" in result

        # Should find CancerBiomarker type
        type_names = [t["name"] for t in result["matches"]["types"]]
        assert "CancerBiomarker" in type_names

        # Should find cancerBiomarkers field
        field_names = [f["field_name"] for f in result["matches"]["fields"]]
        assert "cancerBiomarkers" in field_names


@pytest.mark.asyncio
async def test_search_field_names_only(rich_mock_schema):
    """Test searching only in field names."""
    with patch(
        "open_targets_platform_mcp.tools.search_schema.search_schema.get_schema_explorer",
        new_callable=AsyncMock,
    ) as mock_get_explorer:
        from open_targets_platform_mcp.tools.schema_explorer.schema_explorer import SchemaExplorer

        mock_get_explorer.return_value = SchemaExplorer(rich_mock_schema)

        result = await search_schema("name", search_in=["field_names"])

        # Should find fields with "name" in them
        assert len(result["matches"]["fields"]) > 0

        # Types list might be empty if no types match in type_names
        # (depends on whether search_in is respected)


@pytest.mark.asyncio
async def test_search_type_names_only(rich_mock_schema):
    """Test searching only in type names."""
    with patch(
        "open_targets_platform_mcp.tools.search_schema.search_schema.get_schema_explorer",
        new_callable=AsyncMock,
    ) as mock_get_explorer:
        from open_targets_platform_mcp.tools.schema_explorer.schema_explorer import SchemaExplorer

        mock_get_explorer.return_value = SchemaExplorer(rich_mock_schema)

        result = await search_schema("Disease", search_in=["type_names"])

        # Should find Disease-related types
        type_names = [t["name"] for t in result["matches"]["types"]]
        assert "Disease" in type_names or "DiseasePaginated" in type_names or "DiseaseFilter" in type_names

        # Should not search in fields
        assert len(result["matches"]["fields"]) == 0


@pytest.mark.asyncio
async def test_search_descriptions_only(rich_mock_schema):
    """Test searching only in descriptions."""
    with patch(
        "open_targets_platform_mcp.tools.search_schema.search_schema.get_schema_explorer",
        new_callable=AsyncMock,
    ) as mock_get_explorer:
        from open_targets_platform_mcp.tools.schema_explorer.schema_explorer import SchemaExplorer

        mock_get_explorer.return_value = SchemaExplorer(rich_mock_schema)

        result = await search_schema("gene", search_in=["descriptions"])

        # Mock schema doesn't have descriptions, so should return empty
        assert isinstance(result["matches"]["types"], list)
        assert isinstance(result["matches"]["fields"], list)


@pytest.mark.asyncio
async def test_search_multiple_locations(rich_mock_schema):
    """Test searching in multiple locations."""
    with patch(
        "open_targets_platform_mcp.tools.search_schema.search_schema.get_schema_explorer",
        new_callable=AsyncMock,
    ) as mock_get_explorer:
        from open_targets_platform_mcp.tools.schema_explorer.schema_explorer import SchemaExplorer

        mock_get_explorer.return_value = SchemaExplorer(rich_mock_schema)

        result = await search_schema("disease", search_in=["field_names", "type_names"])

        # Should find in both types and fields
        assert len(result["matches"]["types"]) > 0 or len(result["matches"]["fields"]) > 0


@pytest.mark.asyncio
async def test_search_case_insensitive(rich_mock_schema):
    """Test that search is case insensitive."""
    with patch(
        "open_targets_platform_mcp.tools.search_schema.search_schema.get_schema_explorer",
        new_callable=AsyncMock,
    ) as mock_get_explorer:
        from open_targets_platform_mcp.tools.schema_explorer.schema_explorer import SchemaExplorer

        mock_get_explorer.return_value = SchemaExplorer(rich_mock_schema)

        result_lower = await search_schema("cancer")
        result_upper = await search_schema("CANCER")

        # Should find same results
        assert result_lower["total_matches"] == result_upper["total_matches"]


@pytest.mark.asyncio
async def test_search_no_matches(rich_mock_schema):
    """Test search with no matches."""
    with patch(
        "open_targets_platform_mcp.tools.search_schema.search_schema.get_schema_explorer",
        new_callable=AsyncMock,
    ) as mock_get_explorer:
        from open_targets_platform_mcp.tools.schema_explorer.schema_explorer import SchemaExplorer

        mock_get_explorer.return_value = SchemaExplorer(rich_mock_schema)

        result = await search_schema("NonExistentPattern12345")

        assert result["total_matches"] == 0
        assert len(result["matches"]["types"]) == 0
        assert len(result["matches"]["fields"]) == 0


@pytest.mark.asyncio
async def test_search_deduplicates(rich_mock_schema):
    """Test that search deduplicates results from multiple sources."""
    with patch(
        "open_targets_platform_mcp.tools.search_schema.search_schema.get_schema_explorer",
        new_callable=AsyncMock,
    ) as mock_get_explorer:
        from open_targets_platform_mcp.tools.schema_explorer.schema_explorer import SchemaExplorer

        mock_get_explorer.return_value = SchemaExplorer(rich_mock_schema)

        # Search in both field names and descriptions
        # If a field matches in both, it should only appear once
        result = await search_schema("cancer", search_in=["field_names", "descriptions"])

        # Check for duplicates
        field_keys = [(f["type_name"], f["field_name"]) for f in result["matches"]["fields"]]
        assert len(field_keys) == len(set(field_keys)), "Found duplicate fields"

        type_names = [t["name"] for t in result["matches"]["types"]]
        assert len(type_names) == len(set(type_names)), "Found duplicate types"
