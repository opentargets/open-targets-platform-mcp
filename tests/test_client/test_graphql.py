"""Tests for GraphQL client module."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from otar_mcp.client.graphql import execute_graphql_query, fetch_graphql_schema

# ============================================================================
# fetch_graphql_schema Tests
# ============================================================================


class TestFetchGraphQLSchema:
    """Tests for fetch_graphql_schema function."""

    def test_fetch_schema_success(self, mock_api_endpoint, mock_graphql_client, mock_graphql_schema):
        """Test successful schema fetching."""
        with patch("otar_mcp.client.graphql.Client", return_value=mock_graphql_client):
            schema = fetch_graphql_schema(mock_api_endpoint)
            assert schema is not None
            assert schema == mock_graphql_schema

    def test_fetch_schema_no_schema_raises_error(self, mock_api_endpoint):
        """Test that missing schema raises ValueError."""
        mock_client = MagicMock()
        mock_client.schema = None
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        with patch("otar_mcp.client.graphql.Client", return_value=mock_client):
            with pytest.raises(ValueError, match="Failed to fetch schema"):
                fetch_graphql_schema(mock_api_endpoint)

    def test_fetch_schema_uses_correct_endpoint(self, mock_graphql_schema):
        """Test that the correct endpoint URL is used."""
        custom_endpoint = "https://custom.test/graphql"

        with patch("otar_mcp.client.graphql.RequestsHTTPTransport") as mock_transport:
            mock_client = MagicMock()
            mock_client.schema = mock_graphql_schema
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)

            with patch("otar_mcp.client.graphql.Client", return_value=mock_client):
                fetch_graphql_schema(custom_endpoint)
                mock_transport.assert_called_once_with(url=custom_endpoint)

    @pytest.mark.integration
    def test_fetch_schema_real_api(self, mock_api_endpoint):
        """Integration test: fetch schema from real OpenTargets API."""
        schema = fetch_graphql_schema(mock_api_endpoint)
        assert schema is not None
        assert hasattr(schema, "query_type")


# ============================================================================
# execute_graphql_query Tests - Unit Tests with Mocks
# ============================================================================


class TestExecuteGraphQLQuery:
    """Tests for execute_graphql_query function."""

    def test_execute_query_success(self, mock_api_endpoint, sample_query_string, sample_graphql_response):
        """Test successful query execution."""
        mock_client = MagicMock()
        mock_client.execute.return_value = sample_graphql_response

        with patch("otar_mcp.client.graphql.gql", return_value="parsed_query"):
            with patch("otar_mcp.client.graphql.Client", return_value=mock_client):
                result = execute_graphql_query(mock_api_endpoint, sample_query_string)

        assert result["status"] == "success"
        assert result["data"] == sample_graphql_response
        assert "error" not in result

    def test_execute_query_with_variables(
        self, mock_api_endpoint, sample_query_string, sample_variables, sample_graphql_response
    ):
        """Test query execution with variables."""
        mock_client = MagicMock()
        mock_client.execute.return_value = sample_graphql_response

        with patch("otar_mcp.client.graphql.gql", return_value="parsed_query"):
            with patch("otar_mcp.client.graphql.Client", return_value=mock_client):
                result = execute_graphql_query(mock_api_endpoint, sample_query_string, variables=sample_variables)

        assert result["status"] == "success"
        mock_client.execute.assert_called_once_with("parsed_query", variable_values=sample_variables)

    def test_execute_query_with_custom_headers(self, mock_api_endpoint, sample_query_string):
        """Test query execution with custom headers."""
        custom_headers = {"Authorization": "Bearer token123", "X-Custom": "value"}

        with patch("otar_mcp.client.graphql.RequestsHTTPTransport") as mock_transport:
            with patch("otar_mcp.client.graphql.gql", return_value="parsed_query"):
                with patch("otar_mcp.client.graphql.Client"):
                    execute_graphql_query(mock_api_endpoint, sample_query_string, headers=custom_headers)

        mock_transport.assert_called_once()
        call_kwargs = mock_transport.call_args[1]
        assert call_kwargs["headers"] == custom_headers

    def test_execute_query_invalid_query_string(self, mock_api_endpoint):
        """Test handling of invalid GraphQL query string."""
        invalid_query = "this is not valid graphql"

        with patch("otar_mcp.client.graphql.gql", side_effect=Exception("Parse error")):
            result = execute_graphql_query(mock_api_endpoint, invalid_query)

        assert result["status"] == "error"
        assert "Failed to parse query" in result["message"]
        assert "Parse error" in result["message"]

    def test_execute_query_execution_error(self, mock_api_endpoint, sample_query_string):
        """Test handling of query execution errors."""
        mock_client = MagicMock()
        mock_client.execute.side_effect = Exception("Network error")

        with patch("otar_mcp.client.graphql.gql", return_value="parsed_query"):
            with patch("otar_mcp.client.graphql.Client", return_value=mock_client):
                result = execute_graphql_query(mock_api_endpoint, sample_query_string)

        assert result["status"] == "error"
        assert "Network error" in result["message"]

    def test_execute_query_default_headers(self, mock_api_endpoint, sample_query_string):
        """Test that default headers are set when none provided."""
        with patch("otar_mcp.client.graphql.RequestsHTTPTransport") as mock_transport:
            with patch("otar_mcp.client.graphql.gql", return_value="parsed_query"):
                with patch("otar_mcp.client.graphql.Client"):
                    execute_graphql_query(mock_api_endpoint, sample_query_string)

        call_kwargs = mock_transport.call_args[1]
        assert call_kwargs["headers"] == {"Content-Type": "application/json"}


# ============================================================================
# JQ Filter Tests
# ============================================================================


class TestJQFiltering:
    """Tests for jq filter functionality."""

    def test_execute_query_with_simple_jq_filter(self, mock_api_endpoint, sample_query_string):
        """Test query execution with simple jq filter."""
        mock_response = {
            "target": {"id": "ENSG00000141510", "approvedSymbol": "TP53", "approvedName": "tumor protein p53"}
        }

        mock_client = MagicMock()
        mock_client.execute.return_value = mock_response

        with patch("otar_mcp.client.graphql.gql", return_value="parsed_query"):
            with patch("otar_mcp.client.graphql.Client", return_value=mock_client):
                result = execute_graphql_query(mock_api_endpoint, sample_query_string, jq_filter=".data.target.id")

        # jq filter should extract just the ID
        assert "result" in result
        assert result["result"] == "ENSG00000141510"

    def test_execute_query_with_complex_jq_filter(self, mock_api_endpoint, sample_query_string):
        """Test query execution with object-building jq filter."""
        mock_response = {
            "target": {"id": "ENSG00000141510", "approvedSymbol": "TP53", "approvedName": "tumor protein p53"}
        }

        mock_client = MagicMock()
        mock_client.execute.return_value = mock_response

        with patch("otar_mcp.client.graphql.gql", return_value="parsed_query"):
            with patch("otar_mcp.client.graphql.Client", return_value=mock_client):
                result = execute_graphql_query(
                    mock_api_endpoint, sample_query_string, jq_filter=".data.target | {id, symbol: .approvedSymbol}"
                )

        # jq filter returns a single dict
        assert "id" in result
        assert "symbol" in result
        assert result["id"] == "ENSG00000141510"
        assert result["symbol"] == "TP53"

    def test_execute_query_with_array_jq_filter(self, mock_api_endpoint, sample_query_string):
        """Test query execution with jq filter that returns multiple results."""
        mock_response = {
            "targets": [
                {"id": "ENSG00000141510", "approvedSymbol": "TP53"},
                {"id": "ENSG00000012048", "approvedSymbol": "BRCA1"},
            ]
        }

        mock_client = MagicMock()
        mock_client.execute.return_value = mock_response

        with patch("otar_mcp.client.graphql.gql", return_value="parsed_query"):
            with patch("otar_mcp.client.graphql.Client", return_value=mock_client):
                result = execute_graphql_query(
                    mock_api_endpoint, sample_query_string, jq_filter=".data.targets[] | .approvedSymbol"
                )

        # Multiple results should be wrapped in "results" array
        assert "results" in result
        assert result["results"] == ["TP53", "BRCA1"]

    def test_execute_query_jq_filter_error_handling(self, mock_api_endpoint, sample_query_string):
        """Test that jq filter errors are handled gracefully."""
        mock_response = {"target": {"id": "ENSG00000141510"}}

        mock_client = MagicMock()
        mock_client.execute.return_value = mock_response

        # Mock jq to raise an error
        with patch("otar_mcp.client.graphql.gql", return_value="parsed_query"):
            with patch("otar_mcp.client.graphql.Client", return_value=mock_client):
                with patch("otar_mcp.client.graphql.jq.compile") as mock_jq:
                    # Make jq filter raise an error
                    mock_jq.side_effect = Exception("jq compilation error")

                    result = execute_graphql_query(mock_api_endpoint, sample_query_string, jq_filter=".invalid_filter")

        # Should return success with original data and a warning
        assert result["status"] == "success"
        assert result["data"] == mock_response
        assert "warning" in result
        assert "jq filter failed" in result["warning"]
        assert "// empty" in result["warning"]  # Should suggest null handling

    def test_execute_query_no_jq_filter(self, mock_api_endpoint, sample_query_string, sample_graphql_response):
        """Test query execution without jq filter returns full response."""
        mock_client = MagicMock()
        mock_client.execute.return_value = sample_graphql_response

        with patch("otar_mcp.client.graphql.gql", return_value="parsed_query"):
            with patch("otar_mcp.client.graphql.Client", return_value=mock_client):
                result = execute_graphql_query(mock_api_endpoint, sample_query_string)

        assert result["status"] == "success"
        assert result["data"] == sample_graphql_response


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.integration
class TestGraphQLIntegration:
    """Integration tests with real API calls."""

    def test_real_query_execution(self, mock_api_endpoint):
        """Test real query execution against OpenTargets API."""
        query = """
        query {
            target(ensemblId: "ENSG00000141510") {
                id
                approvedSymbol
            }
        }
        """

        result = execute_graphql_query(mock_api_endpoint, query)

        assert result["status"] == "success"
        assert "data" in result
        assert "target" in result["data"]
        assert result["data"]["target"]["id"] == "ENSG00000141510"
        assert result["data"]["target"]["approvedSymbol"] == "TP53"

    def test_real_query_with_variables(self, mock_api_endpoint):
        """Test real query with variables."""
        query = """
        query GetTarget($ensemblId: String!) {
            target(ensemblId: $ensemblId) {
                id
                approvedSymbol
            }
        }
        """
        variables = {"ensemblId": "ENSG00000012048"}

        result = execute_graphql_query(mock_api_endpoint, query, variables=variables)

        assert result["status"] == "success"
        assert result["data"]["target"]["id"] == "ENSG00000012048"
        assert result["data"]["target"]["approvedSymbol"] == "BRCA1"

    def test_real_query_with_jq_filter(self, mock_api_endpoint):
        """Test real query with jq filter."""
        query = """
        query {
            target(ensemblId: "ENSG00000141510") {
                id
                approvedSymbol
                approvedName
            }
        }
        """

        result = execute_graphql_query(mock_api_endpoint, query, jq_filter=".data.target.approvedSymbol")

        assert "result" in result
        assert result["result"] == "TP53"

    def test_real_invalid_query(self, mock_api_endpoint):
        """Test that invalid query returns error."""
        invalid_query = """
        query {
            nonexistentField {
                id
            }
        }
        """

        result = execute_graphql_query(mock_api_endpoint, invalid_query)

        assert result["status"] == "error"
