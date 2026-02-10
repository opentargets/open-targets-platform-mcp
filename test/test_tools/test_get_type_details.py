"""Tests for get_type_details tool."""

from unittest.mock import AsyncMock, patch

import pytest

from open_targets_platform_mcp.tools.get_type_details.get_type_details import get_type_details


@pytest.mark.asyncio
async def test_get_type_details_object_type(rich_mock_schema):
    """Test getting details for an object type."""
    with patch(
        "open_targets_platform_mcp.tools.get_type_details.get_type_details.get_schema_explorer",
        new_callable=AsyncMock,
    ) as mock_get_explorer:
        from open_targets_platform_mcp.tools.schema_explorer.schema_explorer import SchemaExplorer

        mock_get_explorer.return_value = SchemaExplorer(rich_mock_schema)

        result = await get_type_details("Target")

        assert result["name"] == "Target"
        assert result["kind"] == "OBJECT"
        assert "fields" in result
        assert "implements_interfaces" in result
        assert "Node" in result["implements_interfaces"]

        field_names = [f["name"] for f in result["fields"]]
        assert "id" in field_names
        assert "approvedSymbol" in field_names
        assert "cancerBiomarkers" in field_names


@pytest.mark.asyncio
async def test_get_type_details_with_arguments(rich_mock_schema):
    """Test getting details for type with field arguments."""
    with patch(
        "open_targets_platform_mcp.tools.get_type_details.get_type_details.get_schema_explorer",
        new_callable=AsyncMock,
    ) as mock_get_explorer:
        from open_targets_platform_mcp.tools.schema_explorer.schema_explorer import SchemaExplorer

        mock_get_explorer.return_value = SchemaExplorer(rich_mock_schema)

        result = await get_type_details("Target")

        assoc_diseases = next(f for f in result["fields"] if f["name"] == "associatedDiseases")
        assert len(assoc_diseases["args"]) == 2

        page_arg = next(a for a in assoc_diseases["args"] if a["name"] == "page")
        assert page_arg["type"] == "Int"
        assert page_arg["default_value"] == 0


@pytest.mark.asyncio
async def test_get_type_details_input_type(rich_mock_schema):
    """Test getting details for an input type."""
    with patch(
        "open_targets_platform_mcp.tools.get_type_details.get_type_details.get_schema_explorer",
        new_callable=AsyncMock,
    ) as mock_get_explorer:
        from open_targets_platform_mcp.tools.schema_explorer.schema_explorer import SchemaExplorer

        mock_get_explorer.return_value = SchemaExplorer(rich_mock_schema)

        result = await get_type_details("TargetFilter")

        assert result["name"] == "TargetFilter"
        assert result["kind"] == "INPUTOBJECT"
        assert "fields" in result

        field_names = [f["name"] for f in result["fields"]]
        assert "symbol" in field_names
        assert "minAssociationScore" in field_names


@pytest.mark.asyncio
async def test_get_type_details_enum_type(rich_mock_schema):
    """Test getting details for an enum type."""
    with patch(
        "open_targets_platform_mcp.tools.get_type_details.get_type_details.get_schema_explorer",
        new_callable=AsyncMock,
    ) as mock_get_explorer:
        from open_targets_platform_mcp.tools.schema_explorer.schema_explorer import SchemaExplorer

        mock_get_explorer.return_value = SchemaExplorer(rich_mock_schema)

        result = await get_type_details("EntityType")

        assert result["name"] == "EntityType"
        assert result["kind"] == "ENUM"
        assert "values" in result

        value_names = [v["name"] for v in result["values"]]
        assert "TARGET" in value_names
        assert "DISEASE" in value_names


@pytest.mark.asyncio
async def test_get_type_details_not_found(rich_mock_schema):
    """Test error handling for non-existent type."""
    with patch(
        "open_targets_platform_mcp.tools.get_type_details.get_type_details.get_schema_explorer",
        new_callable=AsyncMock,
    ) as mock_get_explorer:
        from open_targets_platform_mcp.tools.schema_explorer.schema_explorer import SchemaExplorer

        mock_get_explorer.return_value = SchemaExplorer(rich_mock_schema)

        with pytest.raises(ValueError, match="Type 'NonExistent' not found"):
            await get_type_details("NonExistent")


@pytest.mark.asyncio
async def test_get_type_details_error_suggests_similar(rich_mock_schema):
    """Test that error suggests similar type names."""
    with patch(
        "open_targets_platform_mcp.tools.get_type_details.get_type_details.get_schema_explorer",
        new_callable=AsyncMock,
    ) as mock_get_explorer:
        from open_targets_platform_mcp.tools.schema_explorer.schema_explorer import SchemaExplorer

        mock_get_explorer.return_value = SchemaExplorer(rich_mock_schema)

        with pytest.raises(ValueError, match="Did you mean one of.*Target"):
            await get_type_details("Targ")  # Partial match should suggest Target
