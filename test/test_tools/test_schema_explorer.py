"""Tests for SchemaExplorer class."""

from unittest.mock import AsyncMock, patch

import pytest

from open_targets_platform_mcp.tools.schema_explorer.schema_explorer import (
    SchemaExplorer,
    get_schema_explorer,
)


class TestSchemaExplorer:
    """Tests for SchemaExplorer class methods."""

    def test_list_query_fields(self, rich_mock_schema):
        """Test listing all Query root fields."""
        explorer = SchemaExplorer(rich_mock_schema)
        query_fields = explorer.list_query_fields()

        assert len(query_fields) == 4
        assert all("name" in field for field in query_fields)
        assert all("return_type" in field for field in query_fields)
        assert all("args" in field for field in query_fields)

        # Check specific fields
        target_field = next(f for f in query_fields if f["name"] == "target")
        assert target_field["return_type"] == "Target"
        assert "ensemblId: String!" in target_field["args"]

        search_field = next(f for f in query_fields if f["name"] == "search")
        assert "queryString: String!" in search_field["args"]
        assert "page: Int" in search_field["args"]

    def test_list_object_types(self, rich_mock_schema):
        """Test listing all object types."""
        explorer = SchemaExplorer(rich_mock_schema)
        object_types = explorer.list_object_types()

        # Should exclude Query type and introspection types
        type_names = [t["name"] for t in object_types]
        assert "Query" not in type_names
        assert "__Schema" not in type_names

        # Should include our defined types
        assert "Target" in type_names
        assert "Disease" in type_names
        assert "Drug" in type_names
        assert "CancerBiomarker" in type_names

        # Check structure
        target_type = next(t for t in object_types if t["name"] == "Target")
        assert "description" in target_type
        assert "field_count" in target_type
        assert target_type["field_count"] == 6  # id, approvedSymbol, approvedName, cancerBiomarkers, associatedDiseases, proteinAnnotations

    def test_list_input_types(self, rich_mock_schema):
        """Test listing all input types."""
        explorer = SchemaExplorer(rich_mock_schema)
        input_types = explorer.list_input_types()

        type_names = [t["name"] for t in input_types]
        assert "TargetFilter" in type_names
        assert "DiseaseFilter" in type_names

        # Check structure
        target_filter = next(t for t in input_types if t["name"] == "TargetFilter")
        assert "field_count" in target_filter
        assert target_filter["field_count"] == 3

    def test_list_enum_types(self, rich_mock_schema):
        """Test listing all enum types."""
        explorer = SchemaExplorer(rich_mock_schema)
        enum_types = explorer.list_enum_types()

        type_names = [t["name"] for t in enum_types]
        assert "EntityType" in type_names
        assert "ClinicalPhase" in type_names

        # Check values
        entity_type = next(t for t in enum_types if t["name"] == "EntityType")
        assert "values" in entity_type
        assert "TARGET" in entity_type["values"]
        assert "DISEASE" in entity_type["values"]
        assert "DRUG" in entity_type["values"]

    def test_list_scalar_types(self, rich_mock_schema):
        """Test listing custom scalar types (excludes built-ins)."""
        explorer = SchemaExplorer(rich_mock_schema)
        scalar_types = explorer.list_scalar_types()

        type_names = [t["name"] for t in scalar_types]
        assert "JSON" in type_names
        assert "Date" in type_names

        # Built-in scalars should not be included
        assert "String" not in type_names
        assert "Int" not in type_names
        assert "Float" not in type_names
        assert "Boolean" not in type_names
        assert "ID" not in type_names

    def test_get_type_info_object_type(self, rich_mock_schema):
        """Test getting detailed info for an object type."""
        explorer = SchemaExplorer(rich_mock_schema)
        target_info = explorer.get_type_info("Target")

        assert target_info["name"] == "Target"
        assert target_info["kind"] == "OBJECT"
        assert "fields" in target_info
        assert "implements_interfaces" in target_info

        # Check interfaces
        assert "Node" in target_info["implements_interfaces"]

        # Check fields
        field_names = [f["name"] for f in target_info["fields"]]
        assert "id" in field_names
        assert "approvedSymbol" in field_names
        assert "cancerBiomarkers" in field_names
        assert "associatedDiseases" in field_names

        # Check field with arguments
        assoc_diseases = next(f for f in target_info["fields"] if f["name"] == "associatedDiseases")
        assert assoc_diseases["type"] == "DiseasePaginated"
        assert len(assoc_diseases["args"]) == 2

        page_arg = next(a for a in assoc_diseases["args"] if a["name"] == "page")
        assert page_arg["type"] == "Int"
        assert page_arg["default_value"] == 0

    def test_get_type_info_input_type(self, rich_mock_schema):
        """Test getting detailed info for an input type."""
        explorer = SchemaExplorer(rich_mock_schema)
        filter_info = explorer.get_type_info("TargetFilter")

        assert filter_info["name"] == "TargetFilter"
        assert filter_info["kind"] == "INPUTOBJECT"
        assert "fields" in filter_info

        field_names = [f["name"] for f in filter_info["fields"]]
        assert "symbol" in field_names
        assert "minAssociationScore" in field_names

    def test_get_type_info_enum_type(self, rich_mock_schema):
        """Test getting detailed info for an enum type."""
        explorer = SchemaExplorer(rich_mock_schema)
        enum_info = explorer.get_type_info("EntityType")

        assert enum_info["name"] == "EntityType"
        assert enum_info["kind"] == "ENUM"
        assert "values" in enum_info

        value_names = [v["name"] for v in enum_info["values"]]
        assert "TARGET" in value_names
        assert "DISEASE" in value_names

    def test_get_type_info_not_found(self, rich_mock_schema):
        """Test error handling when type doesn't exist."""
        explorer = SchemaExplorer(rich_mock_schema)

        with pytest.raises(ValueError, match="Type 'NonExistent' not found"):
            explorer.get_type_info("NonExistent")

    def test_search_types(self, rich_mock_schema):
        """Test searching for types by name."""
        explorer = SchemaExplorer(rich_mock_schema)

        # Search for "cancer"
        results = explorer.search_types("cancer")
        assert len(results) == 1
        assert results[0]["name"] == "CancerBiomarker"
        assert results[0]["match_reason"] == "type_name"

        # Search for "disease"
        results = explorer.search_types("disease")
        result_names = [r["name"] for r in results]
        assert "Disease" in result_names
        assert "DiseasePaginated" in result_names
        assert "DiseaseFilter" in result_names

        # Case insensitive
        results = explorer.search_types("CANCER")
        assert len(results) == 1
        assert results[0]["name"] == "CancerBiomarker"

    def test_search_fields(self, rich_mock_schema):
        """Test searching for fields by name."""
        explorer = SchemaExplorer(rich_mock_schema)

        # Search for "cancer"
        results = explorer.search_fields("cancer")
        assert len(results) == 1
        assert results[0]["field_name"] == "cancerBiomarkers"
        assert results[0]["type_name"] == "Target"
        assert results[0]["match_reason"] == "field_name"

        # Search for "name"
        results = explorer.search_fields("name")
        field_names = [f"{r['type_name']}.{r['field_name']}" for r in results]
        assert "Disease.name" in field_names
        assert "Drug.name" in field_names
        assert "SearchHit.name" in field_names

    def test_search_descriptions(self, rich_mock_schema):
        """Test searching in descriptions."""
        explorer = SchemaExplorer(rich_mock_schema)

        # Note: Our mock schema doesn't have descriptions, so this will return empty
        results = explorer.search_descriptions("gene")
        assert isinstance(results, list)

    def test_format_type_simple(self, rich_mock_schema):
        """Test formatting simple types."""
        explorer = SchemaExplorer(rich_mock_schema)

        target_type = rich_mock_schema.type_map["Target"]
        id_field = target_type.fields["id"]

        # String! (non-null)
        formatted = explorer._format_type(id_field.type)
        assert formatted == "String!"

        # String (nullable)
        symbol_field = target_type.fields["approvedSymbol"]
        formatted = explorer._format_type(symbol_field.type)
        assert formatted == "String"

    def test_format_type_list(self, rich_mock_schema):
        """Test formatting list types."""
        explorer = SchemaExplorer(rich_mock_schema)

        target_type = rich_mock_schema.type_map["Target"]
        cancer_field = target_type.fields["cancerBiomarkers"]

        # [CancerBiomarker]
        formatted = explorer._format_type(cancer_field.type)
        assert formatted == "[CancerBiomarker]"

    def test_format_type_nested(self, rich_mock_schema):
        """Test formatting complex nested types."""
        explorer = SchemaExplorer(rich_mock_schema)

        disease_paginated = rich_mock_schema.type_map["DiseasePaginated"]
        rows_field = disease_paginated.fields["rows"]

        # [Disease]! (non-null list)
        formatted = explorer._format_type(rows_field.type)
        assert formatted == "[Disease]!"

    def test_is_introspection_type(self, rich_mock_schema):
        """Test introspection type detection."""
        explorer = SchemaExplorer(rich_mock_schema)

        assert explorer._is_introspection_type("__Schema") is True
        assert explorer._is_introspection_type("__Type") is True
        assert explorer._is_introspection_type("__Field") is True
        assert explorer._is_introspection_type("Target") is False
        assert explorer._is_introspection_type("Query") is False

    def test_is_built_in_scalar(self, rich_mock_schema):
        """Test built-in scalar detection."""
        explorer = SchemaExplorer(rich_mock_schema)

        assert explorer._is_built_in_scalar("String") is True
        assert explorer._is_built_in_scalar("Int") is True
        assert explorer._is_built_in_scalar("Float") is True
        assert explorer._is_built_in_scalar("Boolean") is True
        assert explorer._is_built_in_scalar("ID") is True
        assert explorer._is_built_in_scalar("JSON") is False
        assert explorer._is_built_in_scalar("Date") is False


@pytest.mark.asyncio
async def test_get_schema_explorer_caching(rich_mock_schema, clear_schema_cache):
    """Test that SchemaExplorer instance is cached."""
    with patch(
        "open_targets_platform_mcp.tools.schema_explorer.schema_explorer.fetch_graphql_schema",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = rich_mock_schema

        # First call - should fetch
        explorer1 = await get_schema_explorer()
        assert isinstance(explorer1, SchemaExplorer)
        assert mock_fetch.await_count == 1

        # Second call - should use cache
        explorer2 = await get_schema_explorer()
        assert isinstance(explorer2, SchemaExplorer)
        assert mock_fetch.await_count == 1  # Still 1, not called again

        # Should be same instance
        assert explorer1 is explorer2


@pytest.mark.asyncio
async def test_get_schema_explorer_creates_new(rich_mock_schema, clear_schema_cache):
    """Test that get_schema_explorer creates new instance."""
    with patch(
        "open_targets_platform_mcp.tools.schema_explorer.schema_explorer.fetch_graphql_schema",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = rich_mock_schema

        explorer = await get_schema_explorer()
        assert isinstance(explorer, SchemaExplorer)
        assert explorer.schema == rich_mock_schema
        assert mock_fetch.await_count == 1
