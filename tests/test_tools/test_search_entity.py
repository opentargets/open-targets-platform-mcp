"""Tests for search entity tool."""

from unittest.mock import mock_open, patch

import pytest

from otar_mcp.tools.search_entity import _get_search_annotation_query, search_entity

# Access the underlying function (the decorated function is a FunctionTool)
search_entity_fn = search_entity.fn if hasattr(search_entity, "fn") else search_entity


class TestGetSearchAnnotationQuery:
    """Tests for _get_search_annotation_query helper function."""

    def test_get_search_annotation_query_success(self):
        """Test successful loading of SearchAnnotation.gql file."""
        mock_query_content = """
        query SearchAnnotation($queryString: String!) {
            search(queryString: $queryString) {
                hits {
                    id
                    entity
                    name
                }
            }
        }
        """

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=mock_query_content)):
                query = _get_search_annotation_query()

        assert "SearchAnnotation" in query
        assert "queryString" in query

    def test_get_search_annotation_query_file_not_found(self):
        """Test that FileNotFoundError is raised when file doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(FileNotFoundError, match="SearchAnnotation.gql not found"):
                _get_search_annotation_query()


class TestSearchEntity:
    """Tests for search_entity function."""

    def test_search_entity_single_query(self):
        """Test search with single query string."""
        mock_query = "query test { search }"
        mock_response = [{"id": "ENSG00000012048", "entity": "target"}, {"id": "EFO_0000305", "entity": "disease"}]

        with patch("otar_mcp.tools.search_entity._get_search_annotation_query", return_value=mock_query):
            with patch("otar_mcp.tools.search_entity.execute_graphql_query") as mock_execute:
                mock_execute.return_value = mock_response

                result = search_entity_fn(query_strings=["BRCA1"])

        assert "BRCA1" in result
        assert result["BRCA1"] == mock_response

    def test_search_entity_multiple_queries(self):
        """Test search with multiple query strings."""
        mock_query = "query test { search }"
        mock_responses = [
            [{"id": "ENSG00000012048", "entity": "target"}],
            [{"id": "CHEMBL25", "entity": "drug"}],
            [{"id": "EFO_0000305", "entity": "disease"}],
        ]

        with patch("otar_mcp.tools.search_entity._get_search_annotation_query", return_value=mock_query):
            with patch("otar_mcp.tools.search_entity.execute_graphql_query") as mock_execute:
                mock_execute.side_effect = mock_responses

                result = search_entity_fn(query_strings=["BRCA1", "aspirin", "breast cancer"])

        assert "BRCA1" in result
        assert "aspirin" in result
        assert "breast cancer" in result
        assert len(result) == 3

    def test_search_entity_uses_jq_filter(self):
        """Test that search_entity uses the correct jq filter."""
        mock_query = "query test { search }"

        with patch("otar_mcp.tools.search_entity._get_search_annotation_query", return_value=mock_query):
            with patch("otar_mcp.tools.search_entity.execute_graphql_query") as mock_execute:
                mock_execute.return_value = []

                search_entity_fn(query_strings=["test"])

        # Verify the jq filter extracts first 3 results with id and entity only
        call_args = mock_execute.call_args
        assert call_args[1]["jq_filter"] == ".data.search.hits[:3] | map({id, entity})"

    def test_search_entity_passes_correct_variables(self):
        """Test that search_entity passes correct variables for each query."""
        mock_query = "query test { search }"

        with patch("otar_mcp.tools.search_entity._get_search_annotation_query", return_value=mock_query):
            with patch("otar_mcp.tools.search_entity.execute_graphql_query") as mock_execute:
                mock_execute.return_value = []

                search_entity_fn(query_strings=["BRCA1", "TP53"])

        # Check that execute was called twice with correct variables
        assert mock_execute.call_count == 2
        first_call_vars = mock_execute.call_args_list[0][0][2]
        second_call_vars = mock_execute.call_args_list[1][0][2]

        assert first_call_vars == {"queryString": "BRCA1"}
        assert second_call_vars == {"queryString": "TP53"}

    def test_search_entity_query_loading_error(self):
        """Test that query loading errors are returned."""
        with patch("otar_mcp.tools.search_entity._get_search_annotation_query") as mock_get_query:
            mock_get_query.side_effect = FileNotFoundError("File not found")

            result = search_entity_fn(query_strings=["test"])

        assert "error" in result
        assert "File not found" in result["error"]

    def test_search_entity_execution_error(self):
        """Test that execution errors are returned."""
        mock_query = "query test { search }"

        with patch("otar_mcp.tools.search_entity._get_search_annotation_query", return_value=mock_query):
            with patch("otar_mcp.tools.search_entity.execute_graphql_query") as mock_execute:
                mock_execute.side_effect = Exception("Network error")

                result = search_entity_fn(query_strings=["test"])

        assert "error" in result
        assert "Failed to execute search query" in result["error"]

    def test_search_entity_error_response_from_api(self):
        """Test handling of error responses from the API."""
        mock_query = "query test { search }"
        error_response = {"error": "Invalid query"}

        with patch("otar_mcp.tools.search_entity._get_search_annotation_query", return_value=mock_query):
            with patch("otar_mcp.tools.search_entity.execute_graphql_query") as mock_execute:
                mock_execute.return_value = error_response

                result = search_entity_fn(query_strings=["test"])

        # Error response should be returned directly
        assert result == error_response

    def test_search_entity_uses_config_endpoint(self):
        """Test that search_entity uses the config api_endpoint."""
        mock_query = "query test { search }"

        with patch("otar_mcp.tools.search_entity._get_search_annotation_query", return_value=mock_query):
            with patch("otar_mcp.tools.search_entity.execute_graphql_query") as mock_execute:
                mock_execute.return_value = []

                with patch("otar_mcp.tools.search_entity.config") as mock_config:
                    mock_config.api_endpoint = "https://custom.test/graphql"

                    search_entity_fn(query_strings=["test"])

                # Verify the endpoint was used
                call_args = mock_execute.call_args
                assert call_args[0][0] == "https://custom.test/graphql"

    def test_search_entity_empty_query_list(self):
        """Test search with empty query string list."""
        mock_query = "query test { search }"

        with patch("otar_mcp.tools.search_entity._get_search_annotation_query", return_value=mock_query):
            result = search_entity_fn(query_strings=[])

        # Should return empty dict
        assert result == {}

    def test_search_entity_result_structure(self):
        """Test that results are properly structured by query string."""
        mock_query = "query test { search }"
        mock_response = [{"id": "ENSG00000012048", "entity": "target"}, {"id": "EFO_1234", "entity": "disease"}]

        with patch("otar_mcp.tools.search_entity._get_search_annotation_query", return_value=mock_query):
            with patch("otar_mcp.tools.search_entity.execute_graphql_query") as mock_execute:
                mock_execute.return_value = mock_response

                result = search_entity_fn(query_strings=["BRCA1"])

        # Result should be a dict with query string as key
        assert isinstance(result, dict)
        assert "BRCA1" in result
        assert isinstance(result["BRCA1"], list)


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.integration
class TestSearchEntityIntegration:
    """Integration tests with real API calls."""

    def test_real_search_single_gene(self):
        """Test real search for a single gene."""
        result = search_entity_fn(query_strings=["BRCA1"])

        assert "BRCA1" in result
        # jq filter returns list wrapped in {"result": [...]}
        assert "result" in result["BRCA1"]
        assert isinstance(result["BRCA1"]["result"], list)
        assert len(result["BRCA1"]["result"]) > 0

        # First result should be the gene target
        first_result = result["BRCA1"]["result"][0]
        assert "id" in first_result
        assert "entity" in first_result
        assert first_result["entity"] == "target"

    def test_real_search_multiple_entities(self):
        """Test real search for multiple entities."""
        result = search_entity_fn(query_strings=["TP53", "breast cancer", "aspirin"])

        assert "TP53" in result
        assert "breast cancer" in result
        assert "aspirin" in result

        # Extract actual result lists
        tp53_results = result["TP53"]["result"]
        breast_cancer_results = result["breast cancer"]["result"]
        aspirin_results = result["aspirin"]["result"]

        # TP53 should return a target
        assert any(r["entity"] == "target" for r in tp53_results)

        # breast cancer should return a disease
        assert any(r["entity"] == "disease" for r in breast_cancer_results)

        # aspirin should return a drug
        assert any(r["entity"] == "drug" for r in aspirin_results)

    def test_real_search_returns_max_three_results(self):
        """Test that search returns at most 3 results per query."""
        result = search_entity_fn(query_strings=["cancer"])

        assert "cancer" in result
        # Should return at most 3 results due to jq filter
        assert len(result["cancer"]["result"]) <= 3

    def test_real_search_result_format(self):
        """Test that real search results have correct format."""
        result = search_entity_fn(query_strings=["BRCA1"])

        assert "BRCA1" in result
        assert "result" in result["BRCA1"]

        for entity in result["BRCA1"]["result"]:
            # Each result should have only id and entity fields (due to jq filter)
            assert "id" in entity
            assert "entity" in entity
            # Should not have other fields like name, score, etc.
            assert len(entity) == 2
