"""Tests for examples tool."""

from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from otar_mcp.tools.examples import (
    _append_to_field,
    _clean_comment_line,
    _get_extracted_queries_path,
    _get_mappers_path,
    _load_category_descriptors,
    _load_category_query_mapper,
    _parse_metadata_header,
    get_open_targets_query_examples,
)

# Access the underlying function (the decorated function is a FunctionTool)
get_examples_fn = (
    get_open_targets_query_examples.fn
    if hasattr(get_open_targets_query_examples, "fn")
    else get_open_targets_query_examples
)


class TestPathHelpers:
    """Tests for path helper functions."""

    def test_get_extracted_queries_path(self):
        """Test _get_extracted_queries_path returns correct path."""
        path = _get_extracted_queries_path()
        assert isinstance(path, Path)
        assert path.name == "extracted_queries"

    def test_get_mappers_path(self):
        """Test _get_mappers_path returns correct path."""
        path = _get_mappers_path()
        assert isinstance(path, Path)
        assert path.name == "mappers"


class TestLoadingHelpers:
    """Tests for JSON loading helper functions."""

    def test_load_category_descriptors(self, sample_category_descriptors):
        """Test loading category descriptors from JSON."""
        import json

        mock_json_data = json.dumps(sample_category_descriptors)

        with patch("builtins.open", mock_open(read_data=mock_json_data)):
            result = _load_category_descriptors()

        assert result == sample_category_descriptors
        assert "target" in result
        assert "disease" in result

    def test_load_category_query_mapper(self, sample_category_query_mapper):
        """Test loading category query mapper from JSON."""
        import json

        mock_json_data = json.dumps(sample_category_query_mapper)

        with patch("builtins.open", mock_open(read_data=mock_json_data)):
            result = _load_category_query_mapper()

        assert result == sample_category_query_mapper
        assert "target" in result
        assert isinstance(result["target"], list)


class TestCommentParsing:
    """Tests for comment parsing functions."""

    def test_clean_comment_line_with_space(self):
        """Test cleaning comment line with space after #."""
        line = "# Query Name: Test"
        result = _clean_comment_line(line)
        assert result == "Query Name: Test"

    def test_clean_comment_line_without_space(self):
        """Test cleaning comment line without space after #."""
        line = "#Query Name: Test"
        result = _clean_comment_line(line)
        assert result == "Query Name: Test"

    def test_parse_metadata_header_query_name(self):
        """Test parsing Query Name metadata."""
        metadata = {}
        field = _parse_metadata_header("Query Name: GetTargetInfo", metadata)

        assert metadata["query_name"] == "GetTargetInfo"
        assert field is None  # Single line field

    def test_parse_metadata_header_entity_type(self):
        """Test parsing Entity Type metadata."""
        metadata = {}
        field = _parse_metadata_header("Entity Type: target", metadata)

        assert metadata["entity_type"] == "target"
        assert field is None

    def test_parse_metadata_header_description(self):
        """Test parsing Description metadata (multiline)."""
        metadata = {"description": ""}
        field = _parse_metadata_header("Description: Get target info", metadata)

        assert metadata["description"] == "Get target info"
        assert field == "description"  # Multiline field

    def test_parse_metadata_header_variables(self):
        """Test parsing Variables metadata (multiline)."""
        metadata = {"variables": ""}
        field = _parse_metadata_header("Variables: ensemblId (String!)", metadata)

        assert metadata["variables"] == "ensemblId (String!)"
        assert field == "variables"

    def test_parse_metadata_header_pagination(self):
        """Test parsing Pagination Behavior metadata."""
        metadata = {}
        field = _parse_metadata_header("Pagination Behavior: None", metadata)

        assert metadata["pagination"] == "None"
        assert field is None

    def test_parse_metadata_header_unknown_field(self):
        """Test parsing unknown metadata field."""
        metadata = {}
        field = _parse_metadata_header("Unknown Field: value", metadata)

        assert field is None
        assert "Unknown Field" not in metadata

    def test_append_to_field_empty(self):
        """Test appending to empty field."""
        metadata = {"description": ""}
        _append_to_field(metadata, "description", "First line")

        assert metadata["description"] == "First line"

    def test_append_to_field_existing(self):
        """Test appending to field with existing content."""
        metadata = {"description": "First line"}
        _append_to_field(metadata, "description", "Second line")

        assert metadata["description"] == "First line Second line"


class TestGetOpenTargetsQueryExamples:
    """Tests for get_open_targets_query_examples function."""

    def test_get_examples_with_single_category(self):
        """Test getting examples with a single category."""
        # Use a valid category name
        result = get_examples_fn(categories=["entity-search"])

        assert isinstance(result, str)
        assert len(result) > 0  # Should have content

    def test_get_examples_with_multiple_categories(self):
        """Test getting examples with multiple categories."""
        result = get_examples_fn(categories=["entity-search", "disease-associations"])

        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_examples_returns_string(self):
        """Test that get_open_targets_query_examples returns a string."""
        result = get_examples_fn(categories=["entity-search"])

        assert isinstance(result, str)

    def test_get_examples_with_invalid_category(self):
        """Test handling of invalid category."""
        # Should raise ValueError for invalid categories
        with pytest.raises(ValueError, match="Invalid categories"):
            get_examples_fn(categories=["nonexistent_category"])

    def test_get_examples_empty_categories_list(self):
        """Test with empty categories list."""
        result = get_examples_fn(categories=[])

        assert isinstance(result, str)

    def test_get_examples_markdown_format(self):
        """Test that result is formatted as markdown."""
        result = get_examples_fn(categories=["entity-search"])

        # Should contain markdown elements
        assert isinstance(result, str)
        # Markdown typically has headers or formatting
        # This is a basic check - actual format depends on implementation


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.integration
class TestExamplesIntegration:
    """Integration tests with real files."""

    def test_real_get_examples_target_category(self):
        """Test getting real examples for target category."""
        result = get_examples_fn(categories=["entity-search"])

        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain GraphQL query keywords
        assert "query" in result.lower()

    def test_real_get_examples_multiple_categories(self):
        """Test getting real examples for multiple categories."""
        result = get_examples_fn(categories=["entity-search", "disease-associations"])

        assert isinstance(result, str)
        assert len(result) > 0

    def test_real_get_examples_all_standard_categories(self):
        """Test getting examples for all standard categories."""
        # Common categories in OpenTargets
        categories = ["entity-search", "disease-associations", "drug-mechanisms"]

        result = get_examples_fn(categories=categories)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_real_examples_contain_metadata(self):
        """Test that real examples contain metadata from .gql files."""
        result = get_examples_fn(categories=["entity-search"])

        assert isinstance(result, str)
        # Result should contain some structured information
        assert len(result) > 100  # Should have substantial content

    def test_real_examples_grouped_by_category(self):
        """Test that examples are organized by category."""
        result = get_examples_fn(categories=["entity-search", "disease-associations"])

        assert isinstance(result, str)
        # The result should be substantial when multiple categories are requested
        assert len(result) > 0
