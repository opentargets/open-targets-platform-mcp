"""Tests for query tool."""

import json
from unittest.mock import ANY, patch

import pytest

from otar_mcp.tools.query import _query_impl

# Use the internal implementation function directly for testing
query_fn = _query_impl


class TestQueryOpenTargetsGraphQL:
    """Tests for query_open_targets_graphql function."""

    def test_query_returns_dict(self, sample_query_string):
        """Test that query_open_targets_graphql returns a dictionary."""
        with patch("otar_mcp.tools.query.execute_graphql_query") as mock_execute:
            mock_execute.return_value = {"status": "success", "data": {}}

            result = query_fn(sample_query_string)

        assert isinstance(result, dict)

    def test_query_success_without_variables(self, sample_query_string):
        """Test successful query execution without variables."""
        expected_response = {
            "status": "success",
            "data": {"target": {"id": "ENSG00000141510", "approvedSymbol": "TP53"}},
        }

        with patch("otar_mcp.tools.query.execute_graphql_query") as mock_execute:
            mock_execute.return_value = expected_response

            result = query_fn(sample_query_string)

        assert result == expected_response
        mock_execute.assert_called_once_with(
            ANY,  # config.api_endpoint
            sample_query_string,
            None,
            jq_filter=None,
        )

    def test_query_with_dict_variables(self, sample_query_string, sample_variables):
        """Test query execution with dict variables."""
        with patch("otar_mcp.tools.query.execute_graphql_query") as mock_execute:
            mock_execute.return_value = {"status": "success", "data": {}}

            query_fn(sample_query_string, variables=sample_variables)

        # Verify variables were passed as-is (dict)
        call_args = mock_execute.call_args
        assert call_args[0][2] == sample_variables

    def test_query_with_json_string_variables(self, sample_query_string):
        """Test query execution with JSON string variables."""
        variables_json = '{"ensemblId": "ENSG00000141510"}'
        expected_dict = {"ensemblId": "ENSG00000141510"}

        with patch("otar_mcp.tools.query.execute_graphql_query") as mock_execute:
            mock_execute.return_value = {"status": "success", "data": {}}

            query_fn(sample_query_string, variables=variables_json)

        # Verify JSON string was parsed to dict
        call_args = mock_execute.call_args
        assert call_args[0][2] == expected_dict

    def test_query_with_invalid_json_string_variables(self, sample_query_string):
        """Test that invalid JSON string returns error."""
        invalid_json = '{"invalid": json string}'

        result = query_fn(sample_query_string, variables=invalid_json)

        assert "error" in result
        assert "Failed to parse variables JSON string" in result["error"]

    def test_query_with_jq_filter(self, sample_query_string):
        """Test query execution with jq filter (when jq is enabled)."""
        jq_filter = ".data.target.approvedSymbol"

        with patch("otar_mcp.tools.query.execute_graphql_query") as mock_execute:
            mock_execute.return_value = {"result": "TP53"}

            # Enable jq for this test
            with patch("otar_mcp.tools.query.config") as mock_config:
                mock_config.jq_enabled = True
                mock_config.api_endpoint = "https://api.platform.opentargets.org/api/v4/graphql"

                query_fn(sample_query_string, jq_filter=jq_filter)

        # Verify jq_filter was passed
        call_args = mock_execute.call_args
        assert call_args[1]["jq_filter"] == jq_filter

    def test_query_jq_filter_ignored_when_disabled(self, sample_query_string):
        """Test that jq filter is ignored when jq is disabled."""
        jq_filter = ".data.target.approvedSymbol"

        with patch("otar_mcp.tools.query.execute_graphql_query") as mock_execute:
            mock_execute.return_value = {"status": "success", "data": {}}

            # Disable jq for this test
            with patch("otar_mcp.tools.query.config") as mock_config:
                mock_config.jq_enabled = False
                mock_config.api_endpoint = "https://api.platform.opentargets.org/api/v4/graphql"

                query_fn(sample_query_string, jq_filter=jq_filter)

        # Verify jq_filter was NOT passed (should be None)
        call_args = mock_execute.call_args
        assert call_args[1]["jq_filter"] is None

    def test_query_uses_config_endpoint(self, sample_query_string):
        """Test that query uses the config api_endpoint."""
        with patch("otar_mcp.tools.query.execute_graphql_query") as mock_execute:
            mock_execute.return_value = {"status": "success", "data": {}}

            with patch("otar_mcp.tools.query.config") as mock_config:
                mock_config.api_endpoint = "https://custom.test/graphql"
                mock_config.jq_enabled = False

                query_fn(sample_query_string)

            # Verify the endpoint was used
            call_args = mock_execute.call_args
            assert call_args[0][0] == "https://custom.test/graphql"

    def test_query_exception_handling(self, sample_query_string):
        """Test that exceptions are caught and returned as errors."""
        with patch("otar_mcp.tools.query.execute_graphql_query") as mock_execute:
            mock_execute.side_effect = Exception("Unexpected error")

            result = query_fn(sample_query_string)

        assert "error" in result
        assert "Failed to execute GraphQL query" in result["error"]
        assert "Unexpected error" in result["error"]

    def test_query_with_none_variables(self, sample_query_string):
        """Test query with explicitly None variables."""
        with patch("otar_mcp.tools.query.execute_graphql_query") as mock_execute:
            mock_execute.return_value = {"status": "success", "data": {}}

            query_fn(sample_query_string, variables=None)

        # Verify None was passed
        call_args = mock_execute.call_args
        assert call_args[0][2] is None

    def test_query_with_all_parameters(self, sample_query_string, sample_variables):
        """Test query with all parameters provided (jq enabled)."""
        jq_filter = ".data.target.id"

        with patch("otar_mcp.tools.query.execute_graphql_query") as mock_execute:
            mock_execute.return_value = {"result": "ENSG00000141510"}

            # Enable jq for this test
            with patch("otar_mcp.tools.query.config") as mock_config:
                mock_config.jq_enabled = True
                mock_config.api_endpoint = "https://api.platform.opentargets.org/api/v4/graphql"

                query_fn(sample_query_string, variables=sample_variables, jq_filter=jq_filter)

        # Verify all parameters were passed correctly
        mock_execute.assert_called_once_with(
            ANY,  # endpoint
            sample_query_string,
            sample_variables,
            jq_filter=jq_filter,
        )

    def test_query_empty_string_variables(self, sample_query_string):
        """Test that empty string variables are handled."""
        result = query_fn(sample_query_string, variables="")

        # Empty string should fail JSON parsing
        assert "error" in result
        assert "Failed to parse variables JSON string" in result["error"]

    def test_query_complex_json_variables(self, sample_query_string):
        """Test query with complex nested JSON string variables."""
        complex_json = json.dumps({
            "ids": ["ENSG00000141510", "ENSG00000012048"],
            "size": 10,
            "options": {"sort": "relevance"},
        })

        with patch("otar_mcp.tools.query.execute_graphql_query") as mock_execute:
            mock_execute.return_value = {"status": "success", "data": {}}

            query_fn(sample_query_string, variables=complex_json)

        # Verify complex JSON was parsed correctly
        call_args = mock_execute.call_args
        parsed_vars = call_args[0][2]
        assert parsed_vars["ids"] == ["ENSG00000141510", "ENSG00000012048"]
        assert parsed_vars["size"] == 10
        assert parsed_vars["options"]["sort"] == "relevance"


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.integration
class TestQueryIntegration:
    """Integration tests with real API calls."""

    def test_real_query_without_variables(self):
        """Test real query execution without variables."""
        query = """
        query {
            target(ensemblId: "ENSG00000141510") {
                id
                approvedSymbol
            }
        }
        """

        result = query_fn(query)

        assert result["status"] == "success"
        assert result["data"]["target"]["id"] == "ENSG00000141510"
        assert result["data"]["target"]["approvedSymbol"] == "TP53"

    def test_real_query_with_dict_variables(self):
        """Test real query with dict variables."""
        query = """
        query GetTarget($ensemblId: String!) {
            target(ensemblId: $ensemblId) {
                id
                approvedSymbol
            }
        }
        """

        result = query_fn(query, variables={"ensemblId": "ENSG00000012048"})

        assert result["status"] == "success"
        assert result["data"]["target"]["id"] == "ENSG00000012048"
        assert result["data"]["target"]["approvedSymbol"] == "BRCA1"

    def test_real_query_with_json_string_variables(self):
        """Test real query with JSON string variables."""
        query = """
        query GetTarget($ensemblId: String!) {
            target(ensemblId: $ensemblId) {
                id
                approvedSymbol
            }
        }
        """

        result = query_fn(query, variables='{"ensemblId": "ENSG00000139618"}')

        assert result["status"] == "success"
        assert result["data"]["target"]["id"] == "ENSG00000139618"
        assert result["data"]["target"]["approvedSymbol"] == "BRCA2"

    def test_real_query_with_jq_filter(self):
        """Test real query with jq filter (requires jq enabled)."""
        from otar_mcp.config import config

        # Enable jq for this integration test
        original_jq_enabled = config.jq_enabled
        config.jq_enabled = True

        try:
            query = """
            query {
                target(ensemblId: "ENSG00000141510") {
                    id
                    approvedSymbol
                    approvedName
                }
            }
            """

            result = query_fn(query, jq_filter=".data.target | {id, symbol: .approvedSymbol}")

            assert "id" in result
            assert "symbol" in result
            assert result["id"] == "ENSG00000141510"
            assert result["symbol"] == "TP53"
        finally:
            # Restore original value
            config.jq_enabled = original_jq_enabled
